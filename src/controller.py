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
    def __init__(self, base_path):
        self._base_path = base_path
        self._register_testcase = "/commands/registerTestCase"
        self._stop_testcase = "/commands/stopTestcase"

    def register_testcase(self, logger):
        with LiveSession(self._base_path) as s:
            r = s.post(self._register_testcase, timeout=30)
            if r.status_code >= 300:
                r = s.post(self._register_testcase)
            logger.debug(r.text)

    def stop_testcase(self, logger):
        with LiveSession(self._base_path) as s:
            r = s.post(self._stop_testcase, timeout=30)
            logger.debug(r.text)
