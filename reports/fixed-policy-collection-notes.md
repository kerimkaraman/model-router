# Evaluation collection notes — 2026-10-24

The 0.60 candidate was frozen before these OpenAI test-split requests. All 80 Luna answers, 80 Sol answers and 80 Decisions choice judgments were saved.

The Sol run stopped after 60 saved responses because of an OpenAI upstream connection timeout/server error on the next request. The existing 60 records were retained and only the 20 missing question IDs were subsequently submitted. No saved successful answer was regenerated. One extra failed request was attempted; whether it incurred usage is unknown and it is not represented in token-based scenario cost estimates.

The test split was not used to retune the policy. Final result: Luna 75/80, Sol 76/80, fixed cascade 75/80 with seven escalations, no repairs and no regressions.
