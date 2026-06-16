// Shared prompt for the AI insights feature — used by BOTH the Netlify function
// (production) and the Vite dev middleware (local), so the behavior is identical.

export const INSIGHTS_SYSTEM =
  'You are a healthcare facility analyst for Medelite, a managed-services provider ' +
  'evaluating skilled nursing facilities before partnership. Given a facility\'s CMS ' +
  'star ratings and hospitalization/ED metrics, write a concise, factual assessment ' +
  '(3-5 sentences) to inform a partnership decision. Call out clear strengths, any ' +
  'weaknesses (especially a star rating of 1-2 or measures worse than the national ' +
  'average), and end with an overall takeaway. Be specific with the numbers. Note that ' +
  'for hospitalization/ED measures, LOWER is better. Do not give medical advice. ' +
  'Respond in plain prose — no markdown headings or bullet lists.';

// Compress a report model into a compact, factual brief for the model.
export function summarizeReport(r) {
  const ratings = (r.ratings || [])
    .map((x) => `${x.label} ${x.value ?? 'N/A'}/5`)
    .join(', ');
  const metrics = (r.metrics || [])
    .map(
      (m) =>
        `${m.shortName}: facility ${m.facilityText}, state ${m.stateText}, national ` +
        `${m.nationalText} (${m.verdictNational} vs national)`
    )
    .join('; ');
  return (
    `Facility: ${r.name || 'Unknown'} (${r.state || 'Unknown'})\n` +
    `Star ratings: ${ratings || 'none'}\n` +
    `Hospitalization/ED measures (lower is better): ${metrics || 'none'}\n` +
    `QA summary: ${r.qaSummary || 'n/a'}`
  );
}
