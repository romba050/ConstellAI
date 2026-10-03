
ENERGY_AXIS = {"AMPK", "MTOR", "ULK1", "SESTRIN2"}
PI3K_AKT_AXIS = {"PI3K", "AKT"}

def cluster(mechanisms):
    for m in mechanisms:
        g = (m.gene or "").upper()
        if g in ENERGY_AXIS:
            m.pathway = "energy_sensing_axis"
        elif g in PI3K_AKT_AXIS:
            m.pathway = "pi3k_akt_axis"
    return mechanisms
