def describe(provider):
    tenants = {tenant for tenant, _ in provider.rows}
    return {'ready': True, 'partitions': len(tenants)}
