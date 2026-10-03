def translation_risk(evidence):
    human = sum(e["weight"] for e in evidence if e["species"]=="human")
    animal = sum(e["weight"] for e in evidence if e["species"]!="human")
    risk = 0.6
    if human == 0:
        risk += 0.2
    return min(risk, 0.95)