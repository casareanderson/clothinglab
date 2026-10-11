import pytest

from clothinglab import sizes as S

SZ = {"tops": ["M", "L"], "waist": [32], "trouser_length": "regular", "bottoms_letter": ["M"], "shoes_uk": [9, 9.5]}


@pytest.mark.parametrize("label,want", [
    ("XX-Large", "XXL"), ("2XL", "XXL"), ("xl", "XL"), ("Extra Large", "XL"), ("Size L / Black", "L"),
    ("M", "M"), ("Medium", "M"), ("3XL", "3XL"), ("32", None), ("Large Tall", "L"),
])
def test_letters(label, want):
    assert S.letter(label) == want


@pytest.mark.parametrize("label,want", [
    ("W32 L30", (32, "short")), ("32R", (32, "regular")), ("32/34", (32, "long")), ("34", (34, None)),
    ("32 x 32", (32, "regular")), ("M", None), ("99", None),
])
def test_waist(label, want):
    assert S.waist(label) == want


@pytest.mark.parametrize("label,want", [
    ("UK 9", ("uk", 9.0)), ("9.5", (None, 9.5)), ("44 2/3 / Cream / Blue", (None, 44.67)), ("EU 44", ("eu", 44.0)),
    ("US 10", ("us", 10.0)), ("5.5Y", None), ("6 GS", None), ("44,5", (None, 44.5)),
])
def test_shoe_parse(label, want):
    assert S.shoe(label) == want


def test_shoe_scale_eu_is_provable():
    assert S.shoe_scale(["42", "43", "44"]) == "eu"
    assert S.shoe_scale(["8", "9", "10"]) == "uk"
    assert S.shoe_scale(["8", "9"], hint="us") == "us"


def test_shoes_in_my_size():
    assert S.in_my_size("footwear", "9", SZ)
    assert S.in_my_size("footwear", "UK 9.5", SZ)
    assert not S.in_my_size("footwear", "10", SZ)
    assert S.in_my_size("footwear", "44", SZ, scale="eu")         # UK 9 = EU 44
    assert S.in_my_size("footwear", "44.5", SZ, scale="eu")
    assert S.in_my_size("footwear", "43.5", SZ, scale="eu")       # half-size tolerance below
    assert not S.in_my_size("footwear", "45", SZ, scale="eu")
    assert S.in_my_size("footwear", "US 10", SZ)                  # US = UK + 1
    assert not S.in_my_size("footwear", "9.5Y", SZ)


def test_tops_and_bottoms():
    assert S.in_my_size("top", "L", SZ) and S.in_my_size("outer", "Medium", SZ)
    assert not S.in_my_size("top", "XL", SZ)
    assert S.in_my_size("bottom", "32R", SZ)
    assert not S.in_my_size("bottom", "32L", SZ)                  # wrong length when a length is set
    assert S.in_my_size("bottom", "32", SZ)                       # no length stated: fine
    assert S.in_my_size("bottom", "M", SZ)                        # joggers by letter
    assert not S.in_my_size(None, "M", SZ)


def test_my_sizes_stamps_eu():
    assert S.my_sizes("footwear", ["42", "44", "44.5"], SZ, ["42", "43", "44", "44.5", "46"]) == ["EU 44", "EU 44.5"]
