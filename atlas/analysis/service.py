"""Source-closed disease analysis over the existing atlas and curator profiles."""
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from ..store import norm
from . import explain
from .models import (
    AnalyzeRequest, AnalyzeResponse, Assessment, Candidate, Claim, CollaboratorAsset,
    ContractModel, Disease, Experiment, LLMProvenance, RelatedDisease, Source, VariantEffect,
)
from .ranking import load_weights, rank_candidates, score_candidate

EVIDENCE_FILE = Path(__file__).with_name("evidence.json")
SCHEMA_VERSION = "constellai-analysis-v1"
NO_CANDIDATE = "No defensible therapeutic candidate found."


class EvidenceIntegrityError(ValueError):
    """A curator file violated the contract or citation closure."""


class CuratedProfile(ContractModel):
    aliases: list[str]
    disease: Disease
    gene: str
    variant_effect: VariantEffect
    functional_mechanism: Claim
    pathway: Claim
    candidate_treatments: list[dict]
    related_disease_evidence: list[RelatedDisease]
    recommended_next_experiment: Experiment
    collaborators_or_assets: list[CollaboratorAsset]
    limitations: list[str]


class EvidenceLibrary(ContractModel):
    reviewed_on: str
    sources: list[Source]
    profiles: list[CuratedProfile]


def source_references(value):
    """Collect references anywhere in a contract object, never invent citations."""
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    refs = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "source_ids":
                if not isinstance(item, list) or any(not isinstance(s, str) or not s for s in item):
                    raise EvidenceIntegrityError("Invalid source reference list")
                refs.update(item)
            else:
                refs.update(source_references(item))
    elif isinstance(value, list):
        for item in value:
            refs.update(source_references(item))
    return refs


def validate_source_closure(value, sources):
    ledger = {s.id: s for s in sources}
    if len(ledger) != len(sources) or any(not sid.strip() for sid in ledger):
        raise EvidenceIntegrityError("Source IDs must be nonempty and unique")
    if not source_references(value) <= set(ledger):
        raise EvidenceIntegrityError("A claim references a missing source")
    return ledger


class AnalysisService:
    def __init__(self, atlas=None, evidence_path=EVIDENCE_FILE, evidence=None, weights=None):
        self.atlas = atlas
        self.evidence_path = Path(evidence_path)
        self.evidence = evidence
        self.weights = load_weights() if weights is None else weights

    def _library(self):
        try:
            raw = self.evidence if self.evidence is not None else json.loads(self.evidence_path.read_text(encoding="utf-8"))
            library = EvidenceLibrary.model_validate(raw)
            date.fromisoformat(library.reviewed_on)
            ledger = validate_source_closure(library, library.sources)
            for source in library.sources:
                date.fromisoformat(source.reviewed_on)
                parsed = urlsplit(source.url)
                if parsed.scheme not in {"https", "http"} or not parsed.netloc or not source.scope.strip():
                    raise EvidenceIntegrityError("A source requires an ordinary web URL and a declared scope")
            identities = set()
            for profile in library.profiles:
                if not profile.gene.strip() or not profile.disease.id:
                    raise EvidenceIntegrityError("A profile requires a disease identity and gene")
                if not profile.disease.source_ids:
                    raise EvidenceIntegrityError("A curated disease identity requires a source")
                for claim in (profile.variant_effect, profile.functional_mechanism, profile.pathway):
                    if claim.evidence_type != "unknown" and not claim.source_ids:
                        raise EvidenceIntegrityError("Reviewed profile claims require a cited source")
                if profile.disease.id in identities:
                    raise EvidenceIntegrityError("Duplicate curator disease profile")
                identities.add(profile.disease.id)
                if self.atlas is not None:
                    disease = self.atlas.diseases.get(profile.disease.id)
                    if disease is None or profile.gene not in disease["genes"]:
                        raise EvidenceIntegrityError("Profile disease/gene does not match the existing atlas")
                ids = [c.get("id") for c in profile.candidate_treatments]
                if len(set(ids)) != len(ids) or any(not isinstance(cid, str) or not cid for cid in ids):
                    raise EvidenceIntegrityError("Candidate IDs must be nonempty and unique within a profile")
                # Validate all candidates, even when this request uses another profile.
                for candidate in profile.candidate_treatments:
                    self._candidate(candidate, ledger)
            return library, ledger
        except EvidenceIntegrityError:
            raise
        except (ValueError, KeyError, TypeError, OSError) as exc:
            raise EvidenceIntegrityError("Curated evidence could not be validated") from exc

    def _candidate(self, raw, ledger):
        if {"final_score", "score_breakdown", "rank"} & set(raw):
            raise EvidenceIntegrityError("Scores and ranks must be computed by the ranking engine")
        refs = source_references(raw)
        if not refs <= set(ledger):
            raise EvidenceIntegrityError("Candidate source references do not resolve")
        for item in raw.get("sources", []):
            supplied = Source.model_validate(item)
            if supplied.id not in ledger or supplied != ledger[supplied.id]:
                raise EvidenceIntegrityError("Candidate source differs from the canonical ledger")
        breakdown = score_candidate(raw, self.weights)
        candidate = Candidate.model_validate({
            **raw, "sources": [ledger[sid].model_dump() for sid in sorted(refs)],
            "final_score": breakdown.final_score, "score_breakdown": breakdown.model_dump(), "rank": None,
        })
        for field in (
            "mechanism_of_action", "mechanism_alignment", "variant_effect_compatibility",
            "human_evidence", "preclinical_evidence", "phenotype_relevance", "evidence_quality",
            "toxicity", "organ_burden", "drug_interactions", "off_target_spillover", "uncertainty",
        ):
            claim = getattr(candidate, field)
            if claim.evidence_type != "unknown" and not claim.source_ids:
                raise EvidenceIntegrityError("Reviewed candidate claims require a cited source")
        return candidate

    def _resolve(self, query, profiles):
        """Only exact vocabulary matches; no similarity or AI name substitution."""
        nq = norm(query)
        if self.atlas is not None:
            matches = [d for d in self.atlas.diseases.values() if any(
                norm(label) == nq for label in [d["id"], d["name"], *d.get("synonyms", []), *d.get("xrefs", [])]
            )]
            if len(matches) == 1:
                return matches[0], None
            if len(matches) > 1:
                return None, "Disease name is ambiguous; select an exact atlas disease identity."
            genes = [symbol for symbol in self.atlas.genes if norm(symbol) == nq]
            if len(genes) == 1:
                ids = self.atlas.genes[genes[0]]["diseases"]
                if len(ids) == 1:
                    return self.atlas.diseases[ids[0]], None
                return None, "This gene maps to multiple diseases; select an exact disease before therapeutic analysis."
            if len(genes) > 1:
                return None, "Gene name is ambiguous; select an exact gene and disease identity."
        matches = [p for p in profiles if any(
            norm(label) == nq for label in [p.disease.id, p.disease.name, *p.aliases]
        )]
        if len(matches) == 1:
            profile = matches[0]
            if self.atlas is not None:
                return self.atlas.diseases[profile.disease.id], None
            return {"id": profile.disease.id, "name": profile.disease.name, "genes": [profile.gene]}, None
        if len(matches) > 1:
            return None, "Disease alias is ambiguous; select an exact disease identity."
        return None, "No reviewed curator profile was matched to this disease."

    def _empty(self, request, reviewed_on, disease=None, reason=None, sources=None):
        unresolved = "The supplied variant has no reviewed variant-specific functional evidence." if request.variant else "No reviewed functional evidence is available for this input."
        limits = [
            reason or "No reviewed therapeutic profile is available for this disease.",
            "Graph similarity and a gene name do not establish drug efficacy, safety or variant function.",
            "Research output requires expert review before any clinical decision.",
        ]
        if request.variant:
            limits.append(unresolved)
        result = AnalyzeResponse(
            schema_version=SCHEMA_VERSION,
            disease=disease or Disease(id=None, name=request.disease, source_ids=[]),
            gene=request.gene, variant=request.variant,
            variant_effect=VariantEffect(effect="unknown", scope="unresolved", summary=unresolved, evidence_type="unknown", source_ids=[]),
            functional_mechanism=Claim(summary="No reviewed functional mechanism was established for this input.", evidence_type="unknown", source_ids=[]),
            pathway=Claim(summary="No reviewed pathway-based therapeutic evidence was established for this input.", evidence_type="unknown", source_ids=[]),
            candidate_treatments=[], related_disease_evidence=[], collaborators_or_assets=[],
            recommended_next_experiment=Experiment(
                title="Resolve identity and evidence before prioritising compounds",
                question="Which exact disease, gene and variant context should be reviewed?",
                design="Have an appropriate expert confirm disease identity and review primary evidence; obtain variant-specific functional data when a variant is supplied.",
                readouts=["Confirmed disease identity", "Reviewed functional evidence and source record"],
                falsification="If disease identity or functional context cannot be established, withhold therapeutic ranking.",
                prerequisites=["Exact disease identity", "Expert evidence review"], source_ids=[], status="expert_review_required",
            ),
            sources=sources or [], conclusion=NO_CANDIDATE, best_hypothesis_id=None,
            analysis_status="insufficient_evidence", limitations=limits, evidence_reviewed_on=reviewed_on,
            llm=LLMProvenance(mode="cached_evidence", model=None, verified_claims=[], detail="No therapeutic inference was made from an unresolved or unsupported input."),
        )
        if request.use_openai:
            result.llm = LLMProvenance(
                mode="fallback", model=None, verified_claims=[],
                detail="OpenAI verification was skipped because the input has no defensible curated therapeutic profile.",
            )
        validate_source_closure(result, result.sources)
        return result

    def analyze(self, request):
        request = request if isinstance(request, AnalyzeRequest) else AnalyzeRequest.model_validate(request)
        clean = request.model_copy(update={
            "disease": request.disease.strip(), "gene": (request.gene or "").strip().upper() or None,
            "variant": (request.variant or "").strip() or None,
        })
        if not clean.disease or not norm(clean.disease):
            raise ValueError("Disease must contain a name, gene symbol or exact identifier")
        library, ledger = self._library()
        resolved, error = self._resolve(clean.disease, library.profiles)
        if error or resolved is None:
            return self._empty(clean, library.reviewed_on, reason=error)
        profile = next((p for p in library.profiles if p.disease.id == resolved["id"]), None)
        identity = profile.disease.model_copy(deep=True) if profile else Disease(id=resolved["id"], name=resolved["name"], source_ids=[])
        identity_sources = [ledger[sid] for sid in identity.source_ids]
        if clean.gene and clean.gene not in resolved["genes"]:
            return self._empty(clean, library.reviewed_on, identity,
                "The supplied gene conflicts with this disease's atlas identity; therapeutic ranking was withheld.", identity_sources)
        if profile is None:
            if not clean.gene and len(resolved["genes"]) == 1:
                clean = clean.model_copy(update={"gene": resolved["genes"][0]})
            return self._empty(clean, library.reviewed_on, identity, sources=identity_sources)
        if clean.gene and clean.gene != profile.gene:
            return self._empty(clean, library.reviewed_on, identity,
                "The supplied gene has no matching reviewed therapeutic profile for this disease.", identity_sources)
        candidates = [self._candidate(raw, ledger) for raw in profile.candidate_treatments]
        variant_effect = profile.variant_effect.model_copy(deep=True)
        limitations = list(profile.limitations)
        experiment = profile.recommended_next_experiment.model_copy(deep=True)
        if clean.variant:
            variant_effect = VariantEffect(
                effect="unknown", scope="unresolved", evidence_type="unknown", source_ids=[],
                summary="The supplied variant has no reviewed variant-specific functional evidence; gene-level evidence cannot classify its function.",
            )
            limitations.append("The supplied variant is unreviewed. Candidate compatibility and therapeutic eligibility are unresolved; all candidate ranks are withheld.")
            experiment = Experiment(
                title="Establish variant function before compound prioritisation",
                question="What functional effect does the exact supplied variant have in a suitable validated model?",
                design="Have an appropriate expert verify the exact variant identity and choose a validated functional assay with matched controls; review results before adapting disease-context compound hypotheses.",
                readouts=["Variant-specific function compared with matched controls", "Model validity and assay reproducibility"],
                falsification="If variant identity, model validity or functional effect remains unresolved, retain abstention and withhold candidate ranking.",
                prerequisites=["Expert variant review", "Exact variant identity", "Validated variant-specific assay"],
                source_ids=[], status="expert_review_required",
            )
            for candidate in candidates:
                candidate.variant_effect_compatibility = Assessment(
                    value=None, summary="Compatibility is unknown for the supplied unreviewed variant.", evidence_type="unknown", source_ids=[],
                )
                candidate.uncertainty = Assessment(
                    value=1, summary="Variant-specific function and candidate compatibility remain unresolved.", evidence_type="unknown", source_ids=[],
                )
                candidate.status = "insufficient_evidence"
                candidate.rationale += " Ranking withheld: the supplied variant has no reviewed functional evidence."
                candidate.next_validation_step = "Review the exact variant and establish its function in a validated model before considering this disease-context hypothesis."
                candidate.score_breakdown = score_candidate(candidate, self.weights)
                candidate.final_score = candidate.score_breakdown.final_score
                candidate.sources = [ledger[sid] for sid in sorted(source_references(candidate))]
        ranked = rank_candidates(candidates, self.weights)
        best = next((c for c in ranked if c.rank == 1), None)
        result = AnalyzeResponse(
            schema_version=SCHEMA_VERSION, disease=identity, gene=profile.gene, variant=clean.variant,
            variant_effect=variant_effect, functional_mechanism=profile.functional_mechanism,
            pathway=profile.pathway, candidate_treatments=ranked,
            related_disease_evidence=profile.related_disease_evidence,
            recommended_next_experiment=experiment, collaborators_or_assets=profile.collaborators_or_assets,
            sources=[], conclusion=(
                f"{best.compound_name} is the highest-ranked eligible research candidate in the reviewed disease context; "
                "this ranking does not establish clinical benefit or support treatment decisions."
            ) if best else NO_CANDIDATE,
            best_hypothesis_id=best.id if best else None,
            analysis_status="research_hypotheses_found" if best else "insufficient_evidence",
            limitations=limitations, evidence_reviewed_on=library.reviewed_on,
            llm=LLMProvenance(mode="cached_evidence", model=None, verified_claims=[],
                detail="Reviewed source-ledger claims and deterministic curator-rating scoring were used. No OpenAI call was requested."),
        )
        result.sources = [ledger[sid] for sid in sorted(source_references(result))]
        validate_source_closure(result, result.sources)
        if clean.use_openai:
            result.llm = explain.classify_evidence(result)
            validate_source_closure(result, result.sources)
        return result


def analyze(request, atlas=None, **kwargs):
    """Convenient file-backed entry point for fixture generation and integrations."""
    return AnalysisService(atlas=atlas, **kwargs).analyze(request)
