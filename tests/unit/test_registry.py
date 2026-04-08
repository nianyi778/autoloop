import pytest
from modules.base import BaseModule, RoundContext, ModuleResult
from modules.registry import register, get_registry


@register
class FakeModuleForRegistry(BaseModule):
    name = "fake_registry_test"
    description = "测试用 fake 模块"
    match_pattern = r"fake_registry|test_registry"
    evaluation_rubric = None

    async def execute(self, context: RoundContext) -> ModuleResult:
        return ModuleResult(output="fake output")


def test_register_adds_to_registry():
    assert "fake_registry_test" in get_registry()


def test_register_collision_raises():
    with pytest.raises(ValueError, match="collision"):
        @register
        class FakeDuplicate(BaseModule):
            name = "fake_registry_test"  # duplicate
            description = "dup"
            match_pattern = r"dup"
            evaluation_rubric = None

            async def execute(self, context: RoundContext) -> ModuleResult:
                return ModuleResult(output="")


def test_get_registry_returns_copy():
    reg1 = get_registry()
    reg2 = get_registry()
    assert reg1 is not reg2  # defensive copy
    assert reg1 == reg2
