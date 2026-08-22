from agentic_ops_assistant.investigation import InvestigationReport


def build_summary_prompt(report: InvestigationReport) -> str:
    sections = [
        "Summarize the following operations investigation for a human operator.",
        "Use only the supplied report.",
        "Do not propose new actions.",
        "Do not change the policy decision.",
        "Do not claim that an approval was granted unless the report says so.",
        "",
        "INVESTIGATION REPORT",
        "Do not state that a root cause is identified unless the report explicitly confirms one.",
        "Treat retrieved knowledge articles as references, not confirmation of a root cause.",
        "Describe proposed actions as proposals and do not claim that they were executed.",
        "State uncertainty when the report does not establish a conclusion.",
        "Return only a valid JSON object without Markdown or code fences.",
        'Use exactly these fields: "summary", "possible_cause", "uncertainty".',
        '"possible_cause" must be null when the report does not establish a possible cause.',
        '"uncertainty" must state what the report does not confirm.',
        f"Service: {report.service}",
    ]

    if report.service_status is None:
        sections.append("Service status: unknown")
    else:
        sections.extend(
            [
                f"Service health: {report.service_status.health}",
                f"Service summary: {report.service_status.summary}",
            ],
        )

    sections.append("")
    sections.append("Knowledge matches:")

    if not report.knowledge_matches:
        sections.append("- No matching knowledge articles.")
    else:
        for match in report.knowledge_matches:
            sections.extend(
                [
                    f"- Title: {match.article.title}",
                    f"  Score: {match.score}",
                    f"  Content: {match.article.content}",
                ],
            )
    if report.semantic_matches:
        sections.append("")
        sections.append("Semantic knowledge matches:")

        for semantic_match in report.semantic_matches:
            sections.extend(
                [
                    f"- Title: {semantic_match.article.title}",
                    f"  Similarity: {semantic_match.similarity:.3f}",
                    f"  Content: {semantic_match.article.content}",
                ],
            )
    sections.append("")
    if report.proposed_action is None:
        sections.append("Proposed action: none")
    else:
        sections.extend(
            [
                f"Proposed action: {report.proposed_action.action_type}",
                f"Action rationale: {report.proposed_action.rationale}",
            ],
        )

    if report.policy_decision is None:
        sections.append("Policy decision: none")
    else:
        sections.extend(
            [
                f"Policy status: {report.policy_decision.status}",
                f"Policy reason: {report.policy_decision.reason}",
            ],
        )

    return "\n".join(sections)
