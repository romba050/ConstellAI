"""Deterministic projection of reviewed claims and existing atlas provenance.

This is a curated evidence graph. It does not discover therapies, validate
clinical predictions, infer patient variant function, or transfer drug response
between diseases. Atlas annotations enter only when their references resolve to
the reviewed ledger. Investigators enter only as explicitly curated identities.
"""
import hashlib
import re
from urllib.parse import urlsplit

from ..store import norm
from .models import Claim, GraphEdge, GraphNode, KnowledgeGraph, Source

RELATIONSHIPS = {
    "reviewed_gene_association", "reviewed_functional_mechanism", "reviewed_pathway_context",
    "annotated_phenotype", "candidate_under_research", "candidate_evidence_insufficient",
    "candidate_rejected", "reviewed_mechanism_alignment", "reported_human_evidence",
    "preclinical_model_evidence", "shared_research_mechanism", "documented_by",
    "listed_patient_organisation", "registered_study_context", "published_model_reference",
    "documented_resource", "documented_investigator_identity", "reported_variant_example",
    "entered_unreviewed_variant", "unresolved_input_gene",
}
INPUT_RELATIONSHIPS = {"entered_unreviewed_variant", "unresolved_input_gene"}
BASE_LIMITATIONS = [
    "This is a curated evidence graph over reviewed claims and existing atlas identities; it is not newly validated clinical discovery.",
    "Qualitative confidence describes the cited relationship and its scope, not treatment efficacy or an individual prediction.",
    "Shared pathways, phenotype annotations and literature examples do not transfer therapeutic response or classify an entered variant.",
    "Only reviewed source references are projected; unreviewed atlas annotations are omitted.",
    "A paper, registry, organisation or investigator identity does not establish current availability, collaboration or access.",
]


class GraphIntegrityError(ValueError):
    """The graph has a dangling identity, source, or unsupported assertion."""


def _refs(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    if isinstance(value, dict):
        found = set(value.get("source_ids", []))
        for key, item in value.items():
            if key != "source_ids":
                found.update(_refs(item))
        return found
    if isinstance(value, list):
        return set().union(*(_refs(v) for v in value)) if value else set()
    return set()


def _key(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def disease_node_id(disease):
    return "disease:" + (disease.id or "entered:" + _key(disease.name))


def _claim(value):
    return Claim.model_validate(value.model_dump(include={"summary", "evidence_type", "source_ids"}))


def _metadata(source):
    return " ".join((source.title, source.scope, source.excerpt, source.url))


def _reference_index(sources):
    """Resolve actual atlas PMID references to reviewed papers, not fuzzy titles."""
    index = {}
    for source in sources.values():
        pmids = set(re.findall(r"\bPMID\s*:?\s*(\d+)\b", _metadata(source), re.I))
        parsed = urlsplit(source.url)
        if parsed.netloc.lower() == "pubmed.ncbi.nlm.nih.gov" and parsed.path.strip("/").isdigit():
            pmids.add(parsed.path.strip("/"))
        for pmid in pmids:
            index.setdefault(f"PMID:{pmid}", set()).add(source.id)
    return index


def _quality(claim, assertion, contradictions):
    if assertion == "unknown" or not claim.source_ids:
        return "unresolved", "The relationship is unresolved; contextual input does not establish biological function or compatibility."
    if contradictions:
        return "limited", "Cited differences or limiting findings constrain interpretation; differing cohorts and endpoints do not by themselves disprove another study."
    if assertion == "inferred" or claim.evidence_type == "mechanistic_inference":
        return "limited", "Curator interpretation of cited evidence supports a research connection; it is not an observed clinical effect."
    if claim.evidence_type == "preclinical":
        return "limited", "Reported experimental evidence applies to the cited model, genotype and exposure; human translation remains unestablished."
    if claim.evidence_type == "regulatory_label":
        return "strong", "An official label documents this pharmacology or warning within its licensed context; it does not establish benefit for this disease."
    if claim.evidence_type == "human_observational":
        return "moderate", "Reported human observations support this scoped relationship; non-randomized data do not establish causal efficacy."
    if claim.evidence_type in {"trial_registry", "official_resource"}:
        return "moderate", "A dated official resource documents identity or study context; status, eligibility and access require confirmation."
    return "moderate", "The reviewed record supports this relationship within its stated scope; confidence is qualitative and uncalibrated."


def validate_graph(graph, sources, primary_disease_node=None):
    """Fail closed on dangling endpoints/citations, unsourced biology or transfer."""
    graph = graph if isinstance(graph, KnowledgeGraph) else KnowledgeGraph.model_validate(graph)
    ledger = {s.id: s for s in sources}
    if len(ledger) != len(sources):
        raise GraphIntegrityError("Duplicate graph source identity")
    nodes = {n.id: n for n in graph.nodes}
    if len(nodes) != len(graph.nodes) or any(not nid.strip() for nid in nodes):
        raise GraphIntegrityError("Graph node IDs must be nonempty and unique")
    edge_ids = [e.id for e in graph.edges]
    if len(set(edge_ids)) != len(edge_ids) or any(not eid.strip() for eid in edge_ids):
        raise GraphIntegrityError("Graph edge IDs must be nonempty and unique")
    if not _refs(graph) <= set(ledger):
        raise GraphIntegrityError("Graph source reference does not resolve")
    for node in graph.nodes:
        if not node.label.strip() or not node.description.strip():
            raise GraphIntegrityError("Graph nodes require a label and scope description")
        if not node.source_ids and node.kind not in {"disease", "gene", "variant"}:
            raise GraphIntegrityError("Non-input graph nodes require reviewed provenance")
        if len(node.source_ids) != len(set(node.source_ids)):
            raise GraphIntegrityError("Graph node references must be unique")
        if node.url is not None:
            parsed = urlsplit(node.url)
            if not ((parsed.scheme in {"https", "http"} and parsed.netloc)
                    or node.url.startswith("/atlas#")):
                raise GraphIntegrityError("Graph URL is not a permitted source or atlas link")
    for edge in graph.edges:
        if edge.source not in nodes or edge.target not in nodes:
            raise GraphIntegrityError("Graph endpoint does not resolve")
        if edge.source == edge.target:
            raise GraphIntegrityError("A provenance relationship cannot reference itself")
        if edge.relationship_type not in RELATIONSHIPS:
            raise GraphIntegrityError("Graph relationship is outside the reviewed projection")
        if not edge.scope.strip() or not edge.confidence_basis.strip() or not edge.claim.summary.strip():
            raise GraphIntegrityError("Graph relationships require claim, scope and confidence basis")
        if edge.assertion != "unknown" and not edge.claim.source_ids:
            raise GraphIntegrityError("Observed or inferred graph relationships require reviewed sources")
        if not edge.claim.source_ids and edge.relationship_type not in INPUT_RELATIONSHIPS:
            raise GraphIntegrityError("Only explicit unresolved input relationships may be uncited")
        if any(c.evidence_type != "unknown" and not c.source_ids for c in edge.contradictions):
            raise GraphIntegrityError("Known graph limitations require reviewed sources")
        if edge.relationship_type in INPUT_RELATIONSHIPS and (
            edge.assertion != "unknown" or edge.confidence != "unresolved" or edge.claim.source_ids
        ):
            raise GraphIntegrityError("Unreviewed input cannot acquire a functional classification")
        if edge.assertion != "unknown" and (
            not nodes[edge.source].source_ids or not nodes[edge.target].source_ids
        ):
            raise GraphIntegrityError("An observed or inferred relationship has an unsourced endpoint")
        if edge.relationship_type in {"candidate_under_research", "candidate_evidence_insufficient", "candidate_rejected"}:
            if nodes[edge.source].kind != "disease" or nodes[edge.target].kind != "candidate":
                raise GraphIntegrityError("Candidate evidence must retain its disease context")
            if primary_disease_node and edge.source != primary_disease_node:
                raise GraphIntegrityError("Therapeutic evidence cannot transfer across disease contexts")
        if edge.relationship_type in {"reported_human_evidence", "preclinical_model_evidence"}:
            if nodes[edge.source].kind != "candidate" or nodes[edge.target].kind != "disease":
                raise GraphIntegrityError("Candidate observations require their original disease context")
            if primary_disease_node and edge.target != primary_disease_node:
                raise GraphIntegrityError("Candidate response cannot transfer to a related disease")
        if nodes[edge.source].kind == "gene" and nodes[edge.target].kind == "candidate":
            raise GraphIntegrityError("A gene connection does not establish therapeutic efficacy")
    return graph


class _Builder:
    def __init__(self, response, atlas, sources):
        self.response, self.atlas = response, atlas
        self.sources = {s.id: s for s in sources}
        if len(self.sources) != len(sources) or not _refs(response) <= set(self.sources):
            raise GraphIntegrityError("Analysis sources must be closed before graph projection")
        self.reference_index = _reference_index(self.sources)
        self.nodes, self.edges = {}, {}
        self.source_nodes = {}
        self.asset_nodes = {}
        for asset in sorted(response.collaborators_or_assets, key=lambda a: (a.kind, a.name, a.url)):
            if not asset.source_ids or not set(asset.source_ids) <= set(self.sources):
                raise GraphIntegrityError("A research asset requires reviewed sources")
            if asset.kind == "investigator" and not any(
                norm(asset.name) in norm(_metadata(self.sources[sid])) for sid in asset.source_ids
            ):
                raise GraphIntegrityError("Investigator identity is not grounded in reviewed source metadata")
            kind = {"patient_group": "patient_organisation", "study": "clinical_study",
                    "published_model": "research_asset", "resource": "research_asset", "investigator": "investigator"}[asset.kind]
            nid = f"{kind}:asset:{_key(asset.kind + '|' + asset.name + '|' + asset.url)}"
            self.node(nid, kind, asset.name, asset.description + " Access: " + asset.access_status,
                      asset.source_ids, asset.url)
            self.asset_nodes[(asset.kind, asset.name, asset.url)] = nid
            for sid in asset.source_ids:
                source = self.sources[sid]
                if source.url == asset.url and (
                    (source.evidence_type == "trial_registry" and asset.kind == "study")
                    or (source.evidence_type == "official_resource" and asset.kind in {"patient_group", "resource"})
                ):
                    self.source_nodes.setdefault(sid, nid)

    def node(self, nid, kind, label, description, source_ids, url=None):
        source_ids = sorted(set(source_ids))
        if not set(source_ids) <= set(self.sources):
            raise GraphIntegrityError("Graph node source is not reviewed")
        candidate = GraphNode(id=nid, kind=kind, label=label, description=description, source_ids=source_ids, url=url)
        if nid in self.nodes and self.nodes[nid] != candidate:
            previous = self.nodes[nid]
            if previous.model_dump(exclude={"source_ids"}) != candidate.model_dump(exclude={"source_ids"}):
                raise GraphIntegrityError("Graph node identity has conflicting definitions")
            candidate.source_ids = sorted(set(previous.source_ids) | set(candidate.source_ids))
        self.nodes[nid] = candidate
        return nid

    def source_node(self, sid):
        if sid in self.source_nodes:
            return self.source_nodes[sid]
        source = self.sources[sid]
        kind = ("clinical_study" if source.evidence_type == "trial_registry" else
                "paper" if source.evidence_type in {"human_clinical", "human_observational", "preclinical", "mechanistic_inference"}
                else "research_asset")
        nid = f"{kind}:source:{sid}"
        self.node(nid, kind, source.title, source.scope, [sid], source.url)
        self.source_nodes[sid] = nid
        return nid

    def scope(self, refs, prefix):
        return prefix + " " + " ".join(f"[{sid}] {self.sources[sid].scope}" for sid in sorted(set(refs)))

    def edge(self, source, target, relationship, claim, assertion, scope, contradictions=None, basis=None):
        contradictions = contradictions or []
        confidence, confidence_basis = _quality(claim, assertion, contradictions)
        eid = "edge:" + _key("|".join((source, target, relationship)))
        edge = GraphEdge(id=eid, source=source, target=target, relationship_type=relationship,
            claim=claim, confidence=confidence, confidence_basis=basis or confidence_basis,
            assertion=assertion, scope=scope, contradictions=contradictions)
        if eid in self.edges and self.edges[eid] != edge:
            raise GraphIntegrityError("Graph relationship identity has conflicting claims")
        self.edges[eid] = edge

    def provenance(self, owner, refs):
        for sid in sorted(set(refs)):
            source = self.sources[sid]
            record = self.source_node(sid)
            if owner == record:
                continue
            claim = Claim(summary="The curated record cites this reviewed source; source scope: " + source.scope,
                          evidence_type=source.evidence_type, source_ids=[sid])
            self.edge(owner, record, "documented_by", claim, "observed", source.scope,
                basis="This edge records a reviewed citation or resource identity; it does not independently validate every claim or establish clinical benefit.")

    def atlas_references(self, disease):
        refs = set()
        for annotation in disease.get("phenotypes", []):
            for ref in annotation.get("refs", []):
                refs.update(self.reference_index.get(ref.upper(), set()))
        return refs

    def identity(self, disease, gene, refs, *, primary=False):
        dn = self.node(disease_node_id(disease), "disease", disease.name,
            "Reviewed disease context with an atlas navigation anchor; no individual diagnosis is inferred." if disease.id else
            "Unresolved user disease query; no atlas identity or reviewed biological claim was established.",
            refs, f"/atlas#d/{disease.id}" if disease.id else None)
        self.provenance(dn, refs)
        gn = None
        if gene:
            gn = self.node("gene:" + gene, "gene", gene,
                "Gene recorded in this reviewed disease context; this does not classify any individual variant." if refs else
                "Gene symbol supplied or resolved by the atlas; reviewed biological provenance is unavailable for this context.", refs)
            if refs:
                evidence_type = "disease_reference"
                claim = Claim(summary=f"The existing atlas associates {gene} with {disease.name}; reviewed disease references provide the context.",
                              evidence_type=evidence_type, source_ids=sorted(refs))
                self.edge(dn, gn, "reviewed_gene_association", claim, "observed",
                    self.scope(refs, "Disease-level atlas association; not a patient finding or variant-effect assignment."),
                    basis="An existing atlas gene/disease association is anchored to reviewed disease references; no new causal or clinical validation was performed.")
                self.provenance(gn, refs)
        return dn, gn

    def phenotypes(self, disease_node, disease):
        if self.atlas is None:
            return
        hpo = getattr(self.atlas, "hpo", {})
        for annotation in sorted(disease.get("phenotypes", []), key=lambda a: a["hp"]):
            refs = set()
            cited = []
            for ref in sorted(annotation.get("refs", [])):
                matches = self.reference_index.get(ref.upper(), set())
                if matches:
                    cited.append(ref)
                    refs.update(matches)
            hp = annotation["hp"]
            if not refs or hp not in hpo:
                continue
            label = hpo[hp]["name"]
            pn = self.node("phenotype:" + hp, "phenotype", label,
                "Disease-level HPO annotation whose original reference resolves to a reviewed paper; not an individual patient's finding.",
                refs, f"https://hpo.jax.org/browse/term/{hp}")
            claim = Claim(summary=f"The existing atlas records {label} as a phenotype annotation for this disease context.",
                evidence_type="disease_reference", source_ids=sorted(refs))
            self.edge(disease_node, pn, "annotated_phenotype", claim, "observed",
                self.scope(refs, "Original HPO disease annotation; reference(s): " + ", ".join(cited) + ". No new phenotype validation or patient inference."),
                basis="The original HPO annotation cites a reviewed reference; annotation evidence and frequency do not establish an individual finding or a therapeutic response.")
            self.provenance(pn, refs)

    def build(self):
        response = self.response
        model_limits = []
        if response.variant_effect.effect == "variant_dependent" and response.variant_effect.source_ids:
            model_limits.append(Claim(summary="Model and variant limits to interpretation: " + response.variant_effect.summary,
                evidence_type=response.variant_effect.evidence_type, source_ids=response.variant_effect.source_ids))
        for sid in sorted(response.functional_mechanism.source_ids):
            source = self.sources[sid]
            if source.evidence_type == "preclinical" and any(term in source.excerpt.casefold()
                    for term in ("no detectable", "not detect", "no functional", "no phenotype")):
                model_limits.append(Claim(summary="Reported model limit, within its cited assay scope: " + source.excerpt,
                    evidence_type=source.evidence_type, source_ids=[sid]))
        raw = self.atlas.diseases.get(response.disease.id) if self.atlas is not None and response.disease.id else None
        refs = set(response.disease.source_ids) | (self.atlas_references(raw) if raw else set())
        gene = response.gene if raw is None or response.gene in raw.get("genes", []) else None
        if not gene and raw and len(raw.get("genes", [])) == 1:
            gene = raw["genes"][0]
        dn, gn = self.identity(response.disease, gene, refs)
        if response.gene and response.gene != gene:
            entered_gene = self.node("gene:entered:" + _key(response.gene), "gene", response.gene,
                "Supplied gene conflicts with the selected disease context; no association is asserted.", [])
            self.edge(dn, entered_gene, "unresolved_input_gene",
                Claim(summary="The supplied gene has no matching reviewed relationship to the selected disease context.", evidence_type="unknown", source_ids=[]),
                "unknown", "Input identity conflict only; all therapeutic and biological inference from this pairing is withheld.")
        if raw:
            self.phenotypes(dn, raw)
        mechanism, pathway = None, None
        if response.functional_mechanism.source_ids:
            mechanism = self.node("mechanism:" + _key(dn), "mechanism", "Reviewed functional mechanism",
                response.functional_mechanism.summary, response.functional_mechanism.source_ids)
            self.edge(gn or dn, mechanism, "reviewed_functional_mechanism", _claim(response.functional_mechanism),
                "inferred" if response.functional_mechanism.evidence_type == "mechanistic_inference" else "observed",
                self.scope(response.functional_mechanism.source_ids, "Reviewed disease context; model evidence does not classify the entered variant."), model_limits)
            self.provenance(mechanism, response.functional_mechanism.source_ids)
        if response.pathway.source_ids:
            pathway = self.node("pathway:" + _key(dn), "pathway", response.pathway.summary,
                "Reviewed pathway context; membership is not therapeutic efficacy evidence.", response.pathway.source_ids)
            self.edge(mechanism or gn or dn, pathway, "reviewed_pathway_context", _claim(response.pathway),
                "inferred" if response.pathway.evidence_type == "mechanistic_inference" else "observed",
                self.scope(response.pathway.source_ids, "Curated pathway-level context; no drug response is inferred from membership."))
            self.provenance(pathway, response.pathway.source_ids)
        if response.variant:
            vn = self.node("variant:entered:" + _key(response.variant), "variant", response.variant + " (entered; unreviewed)",
                "User-entered variant; identity, transcript, genotype and function remain unreviewed. It is separate from published model examples.", [])
            self.edge(gn or dn, vn, "entered_unreviewed_variant",
                Claim(summary="The entered variant has no reviewed variant-specific functional classification or candidate compatibility.", evidence_type="unknown", source_ids=[]),
                "unknown", "User input only; even matching a short published variant label does not establish matching transcript, zygosity or functional context.")
        # Report only exact variant labels present in the reviewed source excerpt.
        # The edge quotes that source, never classifies an entered variant.
        model_refs = set(response.variant_effect.source_ids)
        if response.functional_mechanism.evidence_type == "preclinical":
            model_refs.update(response.functional_mechanism.source_ids)
        for candidate in response.candidate_treatments:
            model_refs.update(candidate.variant_effect_compatibility.source_ids)
            model_refs.update(candidate.preclinical_evidence.source_ids)
        if gn:
            for sid in sorted(model_refs):
                source = self.sources[sid]
                if source.evidence_type != "preclinical":
                    continue
                for variant in sorted(set(re.findall(r"(?<![A-Za-z0-9])[A-Z][1-9]\d{0,4}[A-Z](?![A-Za-z0-9])", source.excerpt))):
                    vn = self.node(f"variant:reported:{sid}:{variant}", "variant", variant + " (reported example)",
                        "Exact variant label in a reviewed publication excerpt. Source context applies; this is not the entered variant or an individual classification.", [sid], source.url)
                    claim = Claim(summary=source.excerpt, evidence_type=source.evidence_type, source_ids=[sid])
                    self.edge(gn, vn, "reported_variant_example", claim, "observed",
                        self.scope([sid], "Reported literature example only; preserve the cited genotype/model and do not transfer its function to the entered variant."))
                    self.provenance(vn, [sid])
        for candidate in sorted(response.candidate_treatments, key=lambda c: c.id):
            refs = _refs(candidate)
            cn = self.node("candidate:" + candidate.id, "candidate", candidate.compound_name,
                candidate.status + ": " + candidate.rationale, refs)
            contrary = []
            if candidate.human_evidence.source_ids and any(word in candidate.human_evidence.summary.casefold()
                    for word in ("did not find", "conflicting", "contrasting", "heterogeneous")):
                contrary.append(Claim(summary="Limits to comparison across cohorts and endpoints: " + candidate.human_evidence.summary,
                    evidence_type=candidate.human_evidence.evidence_type, source_ids=candidate.human_evidence.source_ids))
            if candidate.toxicity.source_ids and candidate.toxicity.value is not None and candidate.toxicity.value >= .7:
                contrary.append(Claim(summary="Safety findings limit translation; this does not disprove laboratory rescue: " + candidate.toxicity.summary,
                    evidence_type=candidate.toxicity.evidence_type, source_ids=candidate.toxicity.source_ids))
            status = candidate.status
            relationship = ("candidate_rejected" if status == "rejected" else
                            "candidate_evidence_insufficient" if status == "insufficient_evidence" else "candidate_under_research")
            claim = Claim(summary=candidate.rationale, evidence_type="mechanistic_inference", source_ids=sorted(refs))
            self.edge(dn, cn, relationship, claim, "unknown" if status == "insufficient_evidence" else "inferred",
                self.scope(refs, "Disease-context research assessment, not efficacy or treatment advice. " + candidate.next_validation_step), contrary)
            if mechanism and candidate.mechanism_alignment.source_ids:
                self.edge(cn, mechanism, "reviewed_mechanism_alignment", _claim(candidate.mechanism_alignment), "inferred",
                    self.scope(candidate.mechanism_alignment.source_ids, "Curated research alignment; not demonstrated clinical target rescue or individual compatibility."), model_limits)
            for field, relationship in (("human_evidence", "reported_human_evidence"), ("preclinical_evidence", "preclinical_model_evidence")):
                assessment = getattr(candidate, field)
                if assessment.source_ids:
                    self.edge(cn, dn, relationship, _claim(assessment), "observed",
                        self.scope(assessment.source_ids, "Cited study observations in their original scope; no causal efficacy, uniform response or cross-disease transfer is asserted."),
                        contrary if field == "human_evidence" else [])
            self.provenance(cn, refs)
        for related in sorted(response.related_disease_evidence, key=lambda d: (d.disease.id or "", d.gene)):
            refs = set(related.disease.source_ids)
            other_raw = self.atlas.diseases.get(related.disease.id) if self.atlas is not None else None
            if other_raw and related.gene not in other_raw.get("genes", []):
                raise GraphIntegrityError("Related disease identity conflicts with the existing atlas")
            rd, rg = self.identity(related.disease, related.gene, refs)
            self.edge(dn, rd, "shared_research_mechanism", _claim(related.shared_mechanism), "inferred",
                self.scope(related.shared_mechanism.source_ids, related.research_use), [_claim(related.key_difference)])
            if pathway and rg:
                self.edge(rg, pathway, "shared_research_mechanism", _claim(related.shared_mechanism), "inferred",
                    self.scope(related.shared_mechanism.source_ids, "Shared research context only. " + related.research_use), [_claim(related.key_difference)])
        for asset in sorted(response.collaborators_or_assets, key=lambda a: (a.kind, a.name, a.url)):
            an = self.asset_nodes[(asset.kind, asset.name, asset.url)]
            relationship = {"patient_group": "listed_patient_organisation", "study": "registered_study_context",
                "published_model": "published_model_reference", "resource": "documented_resource",
                "investigator": "documented_investigator_identity"}[asset.kind]
            types = {self.sources[sid].evidence_type for sid in asset.source_ids}
            evidence_type = "trial_registry" if "trial_registry" in types else "official_resource" if "official_resource" in types else sorted(types)[0]
            claim = Claim(summary=asset.description, evidence_type=evidence_type, source_ids=asset.source_ids)
            self.edge(dn, an, relationship, claim, "observed",
                self.scope(asset.source_ids, asset.access_status + " Identity or documented resource context only; no availability, efficacy or access is assumed."))
            self.provenance(an, asset.source_ids)
        graph = KnowledgeGraph(nodes=sorted(self.nodes.values(), key=lambda n: n.id),
            edges=sorted(self.edges.values(), key=lambda e: e.id), limitations=list(BASE_LIMITATIONS))
        return validate_graph(graph, list(self.sources.values()), primary_disease_node=dn)


def build_graph(response, atlas=None, sources=None):
    """Project a validated result; ranking and medical claims remain untouched."""
    return _Builder(response, atlas, response.sources if sources is None else sources).build()
