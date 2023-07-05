from pbu.json_wrapper import JSON


def test_dict_compatibility():
    # init
    stats = JSON({
        "win": {
            "total": 0,
        },
    })
    # manipulate using attribute access
    stats.win.total += 1
    assert stats["win"]["total"] == 1
    assert stats.win.total == 1

    # manipulate using key access
    stats["win"]["total"] += 2
    assert stats["win"]["total"] == 3
    assert stats.win.total == 3
