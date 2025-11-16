import os
import schemathesis as st


API_URL = os.getenv("APEX_OPENAPI_URL", "http://localhost:8000/openapi.json")


def test_openapi_contract():
    schema = st.from_uri(API_URL)
    for case in schema.filter_endpoints(methods=("GET",)):
        response = case.call()
        assert 200 <= response.status_code < 500


