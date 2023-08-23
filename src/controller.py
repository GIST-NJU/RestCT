from requests import request, Session, post
from urllib.parse import urljoin


class LiveSession(Session):
    """
    https://stackoverflow.com/questions/42601812/python-requests-url-base-in-session
    """
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url

    def request(self, method, url, *args, **kwargs):
        joined_url = urljoin(self.base_url, url)
        return super().request(method, joined_url, *args, **kwargs)


class RemoteController:
    def __init__(self):
        self._base_path = "http:localhost:8081/commands"
        self._register_testcase = "/registerTestCase"
        self._stop_testcase = "/stopTestcase"

    def register_testcase(self):
        with LiveSession(self._base_path) as s:
            s.post(self._register_testcase)

    def stop_testcase(self):
        with LiveSession(self._base_path) as s:
            s.post(self._stop_testcase)