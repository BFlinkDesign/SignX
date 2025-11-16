from keyedin_mcp_server import table_to_records

def test_nominal():
    table = [["ColA","ColB"], ["v1","v2"], ["v3","v4"]]
    recs = table_to_records(table)
    expected = [{"ColA":"v1","ColB":"v2"},{"ColA":"v3","ColB":"v4"}]
    assert recs == expected
    print("✅ Test passed")

if __name__ == "__main__":
    test_nominal()
