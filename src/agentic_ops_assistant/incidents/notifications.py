from agentic_ops_assistant.incidents.service import DetectedIncident


def format_incident_notification(incident: DetectedIncident) -> str:
    report = incident.investigation
    possible_causes = ", ".join(match.article.title for match in report.knowledge_matches[:3])
    if not possible_causes:
        possible_causes = "Not established from the available evidence."

    if report.proposed_action is None:
        recommended_step = "No operational action is proposed."
    else:
        recommended_step = (
            f"Propose {report.proposed_action.action_type.value}. "
            f"{report.policy_decision.reason if report.policy_decision is not None else ''}"
        ).strip()

    return "\n".join(
        (
            f"Incident detected: {incident.signal.kind.value} ({incident.signal.severity.value})",
            f"Service: {incident.signal.service}",
            f"Evidence: {incident.signal.summary}",
            f"Potential causes: {possible_causes}",
            f"Recommended step: {recommended_step}",
        )
    )
