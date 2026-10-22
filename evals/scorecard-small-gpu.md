# Small-GPU challengers: Gemma 4 E4B and Ministral 3 8B vs Spark-X2.5-4B and Qwen3.5-4B

RTX 2060 6 GB, 2 runs per task, direct tasks only (small models never get agent work). Summary and decision: docs/models.md.

| area | task | agent | model | pass | mean score | mean s | peak ctx |
|---|---|---|---|---|---|---|---|
| longctx | longctx_1_recall | direct | gemma4-e4b | 2/2 | 0.90 | 16 | 0 |
| longctx | longctx_1_recall | direct | ministral3-8b | 0/2 | 0.00 | 0 | 0 |
| longctx | longctx_1_recall | direct | qwen3.5-4b | 2/2 | 1.00 | 45 | 0 |
| longctx | longctx_1_recall | direct | spark-4b | 2/2 | 1.00 | 9 | 0 |
| triage | triage_1_ue_logs | direct | gemma4-e4b | 0/2 | 0.69 | 91 | 0 |
| triage | triage_1_ue_logs | direct | ministral3-8b | 0/2 | 0.38 | 43 | 0 |
| triage | triage_1_ue_logs | direct | qwen3.5-4b | 0/2 | 0.31 | 228 | 0 |
| triage | triage_1_ue_logs | direct | spark-4b | 0/2 | 0.56 | 22 | 0 |
| vision | vision_1_exposure | direct | gemma4-e4b | 0/2 | 0.78 | 71 | 0 |
| vision | vision_1_exposure | direct | ministral3-8b | 0/2 | 0.65 | 24 | 0 |
| vision | vision_1_exposure | direct | qwen3.5-4b | 2/2 | 0.95 | 210 | 0 |
| vision | vision_2_defect | direct | gemma4-e4b | 1/2 | 0.81 | 62 | 0 |
| vision | vision_2_defect | direct | ministral3-8b | 0/2 | 0.62 | 18 | 0 |
| vision | vision_2_defect | direct | qwen3.5-4b | 2/2 | 1.00 | 94 | 0 |
