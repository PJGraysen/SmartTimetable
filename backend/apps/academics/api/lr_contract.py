"""Contract table for LR validation. Single source of truth.

Matches the docx-approved business contract.
"""
from __future__ import annotations

CONTRACT_G10 = {
    ("ENG", "STANDALONE"): 5, ("KIS", "STANDALONE"): 5,
    ("CRE", "STANDALONE"): 4, ("PE", "STANDALONE"): 3,
    ("CSL", "STANDALONE"): 3, ("ICT", "STANDALONE"): 2,
    ("PPI", "STANDALONE"): 1,
    ("COMP", "BLOCK"): 5, ("CHEM", "BLOCK"): 5,
    ("BIO", "BLOCK"): 5, ("GEO", "BLOCK"): 5, ("HIS", "BLOCK"): 5,
    ("PHY", "BLOCK"): 5, ("LIT", "BLOCK"): 5, ("MUSD", "BLOCK"): 5,
    ("AGR", "BLOCK"): 5, ("BUS", "BLOCK"): 5,
}
CONTRACT_G10_E = dict(CONTRACT_G10)
CONTRACT_G10_E[("ESS", "STANDALONE")] = 5
CONTRACT_G10_W = dict(CONTRACT_G10)
CONTRACT_G10_W[("CORE", "STANDALONE")] = 5

CONTRACT_G9 = {
    ("MAT", "STANDALONE"): 5, ("ENG", "STANDALONE"): 5,
    ("KIS", "STANDALONE"): 5, ("SOCIAL", "STANDALONE"): 5,
    ("INTSCI", "STANDALONE"): 5, ("AGR", "STANDALONE"): 5,
    ("CAS", "STANDALONE"): 5, ("CRE", "STANDALONE"): 3,
    ("PPI", "STANDALONE"): 1,
}

CONTRACT_F4 = {
    ("MAT", "STANDALONE"): 6, ("ENG", "STANDALONE"): 5,
    ("KIS", "STANDALONE"): 5, ("CHEM", "STANDALONE"): 5,
    ("PHY", "STANDALONE"): 4, ("BIO", "STANDALONE"): 4,
    ("CRE", "STANDALONE"): 3,
    ("GEO", "BLOCK"): 5, ("HIS", "BLOCK"): 5,
    ("AGR", "BLOCK"): 4, ("BUS", "BLOCK"): 4,
    ("CHEMPRAC", "PRACTICAL"): 2,
    ("BIOPRAC", "PRACTICAL"): 2,
    ("PHYPRAC", "PRACTICAL"): 2,
}


def contract_for(group_code):
    gc = str(group_code).upper()
    if gc.startswith(("10", "11", "12")):
        if gc.endswith("E"):
            return CONTRACT_G10_E
        if gc.endswith("W"):
            return CONTRACT_G10_W
        return CONTRACT_G10
    if gc.startswith("9"):
        return CONTRACT_G9
    if gc.startswith("4"):
        return CONTRACT_F4
    return None
