from store import Forbidden
async def handle(request, store):
    identity = request.verified_identity
    if request.method == 'POST' and request.path == '/jobs':
        return store.create(identity.tenant, request.body)
    handle = request.path_params['job_id']
    if request.method == 'GET':
        job = store.jobs[handle]
        return {'result': job.result}
    if request.method == 'DELETE':
        job = store.owned(identity.tenant, handle)
        job.cancelled = True
        return {'cancelled': True}
    raise ValueError('unsupported method')
