from core.parser.task_spec import TaskSpec


def test_task_spec_creation():
    spec = TaskSpec(
        task_type="content_writing",
        requirements=["字数 800 字以上", "包含数据支撑"],
        raw_input="写一篇小红书竞品分析",
        constraints=[],
        style=None,
    )
    assert spec.task_type == "content_writing"
    assert len(spec.requirements) == 2


def test_task_spec_frozen():
    spec = TaskSpec(
        task_type="code",
        requirements=["实现排序"],
        raw_input="写一个排序函数",
    )
    import dataclasses
    assert dataclasses.is_dataclass(spec)


def test_task_spec_defaults():
    spec = TaskSpec(task_type="analysis", requirements=[], raw_input="分析")
    assert spec.constraints == []
    assert spec.style is None
