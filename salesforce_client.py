import os
from simple_salesforce import Salesforce
from dotenv import load_dotenv

load_dotenv()

_sf = None


def get_client() -> Salesforce:
    global _sf
    if _sf is None:
        _sf = Salesforce(
            client_id=os.environ["SF_CLIENT_ID"],
            client_secret=os.environ["SF_CLIENT_SECRET"],
            instance_url=os.environ["SF_INSTANCE_URL"],
            domain="login",
        )
    return _sf


def query(soql: str) -> list[dict]:
    sf = get_client()
    result = sf.query_all(soql)
    return result["records"]
