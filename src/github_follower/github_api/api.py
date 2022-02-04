import aiohttp
import asyncio
import base64

class GH_API():
    def __init__(self):
        import gf.models as mdl
        self.conn = None
        self.headers = {}

        self.endpoint = 'https://api.github.com'

        self.method = "GET"
        self.url = "/"

        self.response = None
        self.response_code = 0
        self.fails = 0

        # Default user agent.
        user_agent = mdl.Setting.get("user_agent")

        if user_agent is None:
            user_agent = "GitHub-Follower"

        self.add_header("User-Agent", user_agent)

    def add_header(self, key, val):
        self.headers[key] = val
    def add_fail(self):
        self.fails = self.fails + 1

    def authenticate(self, user, token):
        mix = user + ":" + token

        r = base64.b64encode(bytes(mix, encoding='utf8'))

        self.add_header("Authorization", "Basic " + r.decode('ascii'))

    async def send(self, method = "GET", url = "/", headers = {}):
        # Make connection.
        conn = aiohttp.ClientSession()

        # Insert additional headers.
        if self.headers is not None:
            for k, v in self.headers.items():
                headers[k] = v

        res = None
        status = None
        failed = False

        # Send request.
        try:
            if method == "POST":
                res = await conn.post(self.endpoint + url, headers = headers)
            elif method == "PUT":
                res = await conn.put(self.endpoint + url, headers = headers)
            elif method == "DELETE":
                res = await conn.delete(self.endpoint + url, headers = headers)
            else:
                res = await conn.get(self.endpoint + url, headers = headers)
        except Exception as e:
            print(e)

            failed = True

        if not failed and res is not None:
            status = res.status
            res = await res.text()

        # Close connection.
        try:
            await conn.close()
        except Exception as e:
            print("[ERR] HTTP close error.")
            print(e)

            return [None, 0]
        else:
            # Set fails to 0 indicating we closed the connection.
            if not failed and res is not None:
                self.fails = 0
        
        # Return list (response, response code)
        return [res, status]