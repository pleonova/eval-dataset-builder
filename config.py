# Krippendorff's alpha status: good >= 0.80, fair 0.67 to 0.80, weak < 0.67
ALPHA_GOOD = 0.80
ALPHA_FAIR = 0.67

# Ordered levels, coded 1 to 4
LEVELS = ["slightly_complex", "moderately_complex", "very_complex", "exceedingly_complex"]
CRITERIA = ["sentence_structure", "vocabulary", "background_knowledge"]

# Share of item-criterion pairs in the Trusted bucket: good >= 0.80, fair 0.60 to 0.80, weak < 0.60
TRUSTED_GOOD = 0.80
TRUSTED_FAIR = 0.60

BUCKETS = ["Trusted", "Re-rate", "No expert consensus"]

# Share of items where all 3 judge runs agree: good >= 0.90, fair 0.75 to 0.90, weak < 0.75 (judgment call)
SELF_CONSISTENCY_GOOD = 0.90
SELF_CONSISTENCY_FAIR = 0.75

# Flag a criterion when round 1 split on at least this share of its items, so it needed a second
# expert round. Judgment call: set to catch the confusing criterion, not the subjective slice.
ROUND2_FLAG_SHARE = 0.45

# Cost of a re-rate round (example values): new experts per split label, minutes per label, $ per expert hour
RERATE_EXPERTS = 2
MINUTES_PER_LABEL = 6
COST_PER_HOUR = 60

# "More ratings" chart: extra passages to project the Trusted share range for (example values)
EXTRA_PASSAGES = [30, 60]

# Rubric tab: a rubric rule is clear when AI raters agree (alpha >= ALPHA_FAIR) and change their answer
# on at most this share of passages (judgment call)
RUBRIC_MAX_FLIP = 0.20

# Rubric tab savings line: one expert round on the rubric (example values)
PILOT_ITEMS = 30
PILOT_EXPERTS = 3
REVISION_ROUNDS = 3
