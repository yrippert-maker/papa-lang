"""Semantic checks for .papa AST."""

from .ast_nodes import Program

VALID_MODULES = {
    "papa-life",
    "papa-finance",
    "papa-legal",
    "papa-devops",
    "papa-docs",
    "papa-ai-hub",
    "papa-app",
    "",
}


class ValidationError(Exception):
    pass


class Validator:
    def validate(self, program: Program) -> list:
        """Returns list of warnings (empty = valid). Raises ValidationError on fatal issues."""
        errors = []

        agent_names = {a.name for a in program.agents}

        for swarm in program.swarms:
            for agent_ref in swarm.agents:
                if agent_ref not in agent_names:
                    raise ValidationError(
                        f'Line {swarm.line}: Agent "{agent_ref}" not defined'
                    )

        for agent in program.agents:
            if not 0 <= agent.hrs_threshold <= 1:
                raise ValidationError(
                    f"Line {agent.line}: hrs_threshold must be 0.0-1.0"
                )
            if agent.retrieval == "graph" and not agent.memory:
                raise ValidationError(
                    f"Line {agent.line}: Agent {agent.name!r} retrieval: graph "
                    "requires memory: enabled"
                )

        for swarm in program.swarms:
            if swarm.consensus:
                if swarm.consensus.required > swarm.consensus.of:
                    raise ValidationError(
                        f"Line {swarm.line}: consensus "
                        f"{swarm.consensus.required}/{swarm.consensus.of} is invalid"
                    )

        for pipeline in program.pipelines:
            if pipeline.module not in VALID_MODULES:
                errors.append(
                    f'Warning: unknown module "{pipeline.module}"'
                )

        return errors
