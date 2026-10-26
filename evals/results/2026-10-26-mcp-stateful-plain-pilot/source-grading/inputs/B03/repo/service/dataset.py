from copy import deepcopy

class Dataset:
    def __init__(self):
        self.rows = {('north', 'general'): [
            {'id': 'one', 'body': 'North editorial record'},
            {'id': 'two', 'body': 'North financial record'},
            {'id': 'three', 'body': 'North planning record'}],
            ('south', 'general'): [{'id': 'one', 'body': 'South working record'}]}

    def select(self, tenant, project, cursor, size):
        rows = self.rows.get((tenant, project), [])
        items = deepcopy(rows[cursor:cursor + size])
        return items, cursor + len(items) >= len(rows)
