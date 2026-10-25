from typing import Any, Protocol, TypeVar
from uuid import UUID, uuid4


from pydantic import BaseModel, Field

class AgentTask(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID = Field(default_factory=uuid4)
    agent_name: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    
class AgentResult(BaseModel):
    task_id: UUID
    workflow_id: UUID
    agent_name: str
    customer_id: str
    output: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"

class CoverageAgent(Protocol):
    name: str

    async def execute(self, task: AgentTask) -> AgentResult:
        ...
        
class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, CoverageAgent] = {}
        
    def register(self, agent: CoverageAgent):
        if agent.name in self._agents:
            raise ValueError(f"Agent with name '{agent.name}' is already registered.")
        self._agents[agent.name] = agent
        
    def get_agent(self, name: str) -> CoverageAgent:
        if name not in self._agents:
            raise ValueError(f"Agent with name '{name}' is not registered.")
        return self._agents[name]
    
    def list_agents(self) -> list[str]:
       return sorted(self._agents.keys())
    
class CoverageOrchestrator:
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        
    
    async def run_agent(self, task: AgentTask) -> AgentResult:
        agent = self.registry.get_agent(task.agent_name)
        result = await agent.execute(task)

        if result.task_id != task.task_id:
            raise ValueError("Agent returned incorrect task ID")

        if result.agent_name != task.agent_name:
            raise ValueError("Agent returned incorrect name")

        return result

    async def run_sequence(
        self,
        customer_id: str,
        steps: list[str],
        initial_payload: dict[str, Any],
        workflow_id: UUID | None = None,
    ) -> list[AgentResult]:
        workflow_id = workflow_id or uuid4()
        payload = dict(initial_payload)
        results: list[AgentResult] = []

        for agent_name in steps:
            task = AgentTask(
                workflow_id=workflow_id,
                customer_id=customer_id,
                agent_name=agent_name,
                payload=dict(payload),
            )

            result = await self.run_agent(task)
            results.append(result)

            if result.status != "completed":
                break

            payload[agent_name] = result.output

        return results