import requests

MAX_TAGS = 50
MAX_TAG_LEN = 1000

class ClassTagger:
    def __init__(self, workspace_url: str, pat: str, prefix: str = "tx_"):
        self.workspace_url = workspace_url
        self.pat = pat
        self.prefix = prefix

    def _securable_url(self, securable_type: str, securable_name: str):
        if securable_type == 'COLUMN':
            table, column = securable_name.rsplit('.', 1)
            return f"https://{self.workspace_url}/api/2.0/unity-catalog/tag-assignments/TABLE/{table}/COLUMN/{column}"
        return f"https://{self.workspace_url}/api/2.0/unity-catalog/tag-assignments/{securable_type}/{securable_name}"

    def list_tags(self, securable_type: str, securable_name: str) -> dict:
        res = requests.get(self._securable_url(securable_type, securable_name),
                           headers={"Authorization": f"Bearer {self.pat}"})
        res.raise_for_status()
        return {t['tag_key']: t.get('tag_value', '')
                for t in res.json().get('tag_assignments', [])}

    def apply_tags(self, securable_type: str, securable_name: str, *tags: str):
        # TODO check the tag string is not too long
        new_tags = set(self.prefix + tag for tag in tags)
        current_tags = self.list_tags(securable_type, securable_name)
        old_tags = set(t for t in current_tags if t.startswith(self.prefix))

        to_add = new_tags - old_tags
        to_del = old_tags - new_tags

        if len(current_tags) + len(to_add) - len(to_del) >= MAX_TAGS:
            raise Exception(f"too many tags on {securable_type} {securable_name}!")


        print(f"removing tags {to_del} from {securable_type} {securable_name}")
        for tag in to_del:
            self._delete_tag(securable_type, securable_name, tag)

        print(f"adding tags {to_add} to {securable_type} {securable_name}")
        for tag in to_add:
            self._add_tag(securable_type, securable_name, tag)

    def _delete_tag(self, securable_type: str, securable_name: str, tag):
        url = self._securable_url(securable_type, securable_name)
        url += "/" + tag
        res = requests.delete(url, headers={"Authorization": f"Bearer {self.pat}"})
        res.raise_for_status()

    def _add_tag(self, securable_type: str, securable_name: str, tag):
        res = requests.post(self._securable_url(securable_type, securable_name),
                            headers={"Authorization": f"Bearer {self.pat}"},
                            json={"tag_key": tag})
        if res.status_code not in (200, 409):
            res.raise_for_status()

    def clear_tags(self, securable_type: str, securable_name: str):
        current_tags = self.list_tags(securable_type, securable_name)
        to_del = set(t for t in current_tags if t.startswith(self.prefix))

        print(f"removing tags {to_del} from {securable_type} {securable_name}")
        for tag in to_del:
            self._delete_tag(securable_type, securable_name, tag)





