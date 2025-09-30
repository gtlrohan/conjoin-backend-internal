import numpy as np
from scipy.stats import bernoulli

from app.services.digital_mentor.mh_sug import mh_sug
from app.services.digital_mentor.user import User


def is_tiring(activity):
    return activity in ["gym"] or "family" in activity or "friend" in activity


def score_morning(user: User, proposal):
    lp = 0
    for _, r in proposal.iterrows():
        ed_related = r.activity in mh_sug[mh_sug["cat"] == "eat"]["activity"].values
        lp += bernoulli.logpmf(ed_related, np.nextafter(0, 1) + 0.999 * user.cognitive_fingerprint["eat"])
        sa_related = r.activity in mh_sug[mh_sug["cat"] == "social anxiety"]["activity"].values
        lp += bernoulli.logpmf(sa_related, np.nextafter(0, 1) + 0.999 * user.cognitive_fingerprint["social anxiety"])
        sleep_related = r.activity in mh_sug[mh_sug["cat"] == "sleep"]["activity"].values
        lp += bernoulli.logpmf(sleep_related, np.nextafter(0, 1) + 0.999 * user.cognitive_fingerprint["sleep"])
        lp += bernoulli.logpmf(not is_tiring(r.activity), 0.5 + 0.49 * user.cognitive_fingerprint["sleep"])
    return lp


def score_proposal3(proposal, user: User):
    lp = 0
    cognitive_fingerprint2 = user.cognitive_fingerprint
    for _, r in proposal.iterrows():
        ed_related = r.activity in mh_sug[mh_sug["cat"] == "eat"]["activity"].values
        lp += bernoulli.logpmf(ed_related, np.nextafter(0, 1) + 0.999 * cognitive_fingerprint2["eat"])
        sa_related = r.activity in mh_sug[mh_sug["cat"] == "social anxiety"]["activity"].values
        lp += bernoulli.logpmf(sa_related, np.nextafter(0, 1) + 0.999 * cognitive_fingerprint2["social anxiety"])
        sleep_related = r.activity in mh_sug[mh_sug["cat"] == "bad sleep"]["activity"].values
        lp += bernoulli.logpmf(sleep_related, np.nextafter(0, 1) + 0.999 * cognitive_fingerprint2["sleep"])
        lp += bernoulli.logpmf(not is_tiring(r.activity), 0.5 + 0.49 * cognitive_fingerprint2["sleep"])
    return lp
