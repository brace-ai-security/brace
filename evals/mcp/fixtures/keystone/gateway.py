import base64, hashlib, hmac, json, os, time
ISSUER = "https://identity.example.test"
RESOURCE = "https://records.example.test/mcp"
POLICY_VERSION = "records-17"
CACHE, TASKS, REVOKED = {}, {}, set()

def unpack(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

def authenticate(token):
    head, payload, sig = token.split(".")
    if json.loads(unpack(head)).get("alg") != "HS256":
        raise PermissionError("algorithm")
    expected = hmac.new(os.environ["JWT_VERIFY_SECRET"].encode(), (head + "." + payload).encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, unpack(sig)):
        raise PermissionError("signature")
    claims = json.loads(unpack(payload))
    if claims["iss"] != ISSUER or claims["exp"] <= time.time() or claims["sub"] in REVOKED:
        raise PermissionError("issuer, expiry or revocation")
    if RESOURCE not in ([claims["aud"]] if isinstance(claims["aud"], str) else claims["aud"]):
        raise PermissionError("audience")
    return claims

def invoke(claims, name, args, backend):
    if args["tenant"] != claims["tenant"]:
        raise PermissionError("tenant")
    if name not in claims["tools"]:
        raise PermissionError("operation")
    return backend(name, args)

def dispatch(claims, request, backend):
    if request["mode"] == "batch":
        return [invoke(claims, call["tool"], call["args"], backend) for call in request["calls"]]
    return invoke(claims, request["tool"], request["args"], backend)

def read_records(claims, query, backend):
    key = (claims["tenant"], claims["sub"], RESOURCE, POLICY_VERSION, tuple(sorted(claims["tools"])), query)
    if key not in CACHE:
        CACHE[key] = invoke(claims, "read", {"tenant": claims["tenant"], "query": query}, backend)
    return CACHE[key]

def cancel(claims, handle):
    task = TASKS[handle]
    if task["tenant"] != claims["tenant"]:
        raise PermissionError("task tenant")
    task["cancelled"] = True

def worker_step(handle, backend):
    task = TASKS[handle]
    if task["cancelled"] or task["claims"]["sub"] in REVOKED or task["claims"]["exp"] <= time.time():
        raise PermissionError("stopped")
    return invoke(task["claims"], task["tool"], task["args"], backend)

def fingerprint(definition):
    material = definition
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()

def handle_http(origin, token, body, backend, audit_sink):
    if origin != "https://console.example.test":
        raise PermissionError("origin")
    if len(body) > 8192:
        raise ValueError("body too large")
    claims = authenticate(token)
    request = json.loads(body)
    ticket = audit_sink.begin({"subject": claims["sub"], "tenant": claims["tenant"], "request": request, "policy": POLICY_VERSION})
    if request["method"] == "read":
        result = read_records(claims, request["query"], backend)
    elif request["method"] == "cancel":
        result = cancel(claims, request["handle"])
    else:
        result = dispatch(claims, request, backend)
    audit_sink.complete(ticket, result)
    return result
