import pytest
from modules.base import BaseModule, RoundContext, ModuleResult
from modules.registry import register, get_registry
from modules.router import MatchRouter, NoModuleFound, AmbiguousModuleMatch
from core.parser.task_spec import TaskSpec


# Register test module (won't collide if name is unique)
@register
class RouterTestModule(BaseModule):
    name = "router_test_module"
    description = "Router test module"
    match_pattern = r"router_test_type"
    evaluation_rubric = None

    async def execute(self, context: RoundContext) -> ModuleResult:
        return ModuleResult(output="router test output")


def make_spec(task_type: str) -> TaskSpec:
    return TaskSpec(task_type=task_type, requirements=(), raw_input="test")


@pytest.mark.asyncio
async def test_router_unique_match():
    router = MatchRouter()
    result = await router.route(make_spec("router_test_type"))
    assert result.name == "router_test_module"


@pytest.mark.asyncio
async def test_router_no_match_raises():
    router = MatchRouter()
    with pytest.raises(NoModuleFound):
        await router.route(make_spec("completely_unknown_xyz_99999"))


@pytest.mark.asyncio
async def test_router_cache_works():
    router = MatchRouter()
    spec = make_spec("router_test_type")
    result1 = await router.route(spec)
    result2 = await router.route(spec)
    assert result1 is result2  # same class object returned


@pytest.mark.asyncio
async def test_router_case_insensitive():
    router = MatchRouter()
    result = await router.route(make_spec("ROUTER_TEST_TYPE"))
    assert result.name == "router_test_module"
