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
