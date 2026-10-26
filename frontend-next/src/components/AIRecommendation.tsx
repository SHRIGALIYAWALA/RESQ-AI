interface AIRecommendationProps {
  analysis: Record<string, unknown> | null;
}

export function AIRecommendation({ analysis }: AIRecommendationProps) {
  if (!analysis) {
    return (
      <div className="rounded-lg border border-white/10 bg-card p-4 text-sm text-muted">
        Select an incident to view AI recommendations. All outputs require human authorization.
      </div>
    );
  }

  const decision = (analysis.decision as Record<string, unknown>) || {};
  const evacuation = (analysis.evacuation_plan as Record<string, unknown>) || {};
  const communication = (analysis.communication || analysis.communications) as Record<string, unknown> | undefined || {};
  const incidentClassification = (analysis.incident_classification as Record<string, unknown>) || {};
  const classification = (incidentClassification.classification as Record<string, unknown>) || {};

  const safeExits = (evacuation.safe_exits || evacuation.primary_safe_exits) as string[] | undefined;
  const recommendedActions = Array.isArray(classification.recommended_actions)
    ? classification.recommended_actions as string[]
    : [];
  const recommendedAction = (decision.recommended_action as string)
    || (evacuation.primary_action as string)
    || recommendedActions[0];
  const citizenInstructions = (communication.citizen_instructions
    || communication.announcement_script_en
    || communication.citizen_alert) as string | undefined;
  const humanApprovalRequired = decision.human_approval_required === true
    || analysis.human_authorization_required === true;

  return (
    <div className="space-y-3 text-sm">
      <div className="rounded-lg border border-purple-500/30 bg-purple-500/5 p-3">
        <p className="font-mono text-xs text-purple-400">AI RECOMMENDATION</p>
        <p className="mt-2 font-semibold">
          {recommendedAction || (classification.summary as string) || "Analysis complete; no action text was returned."}
        </p>
        {humanApprovalRequired && (
          <p className="mt-1 text-xs text-warning">⚠ Human approval required before broadcast</p>
        )}
      </div>
      {safeExits && safeExits.length > 0 && (
        <div className="rounded border border-safe/30 bg-safe/5 p-2">
          <p className="text-xs text-safe">Safe exits: {safeExits.join(", ")}</p>
        </div>
      )}
      {citizenInstructions && (
        <div className="rounded border border-cyan-500/20 bg-card p-2 font-mono text-xs leading-relaxed">
          {citizenInstructions}
        </div>
      )}
    </div>
  );
}
