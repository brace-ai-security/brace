from service.limits import bounded_list, text
from service.errors import InvalidRequest

def test_text_keeps_valid_identifiers():
    assert text("north", "tenant") == "north"
    assert text("public/guide", "record") == "public/guide"

def test_batch_has_a_finite_bound():
    assert bounded_list([1]) == [1]
    try:
        bounded_list(list(range(9)))
    except InvalidRequest:
        return
    assert False, "oversize batch accepted"

def test_control_characters_are_rejected():
    try:
        text("bad\nname", "record")
    except InvalidRequest:
        return
    assert False, "control character accepted"
