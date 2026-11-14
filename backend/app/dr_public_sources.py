"""Operator-recorded public dataset evidence, separate from clinical grading."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, max_length=1000)]


class PublicDatasetEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    schema_version: Literal['carebalance.public-retinal-source.v1']
    dataset_title: Literal['MMRDR']
    dataset_doi: Literal['10.6084/m9.figshare.29423747.v2']
    dataset_url: Literal['https://figshare.com/articles/dataset/MMRDR/29423747']
    license_id: Literal['CC-BY-4.0']
    license_url: Literal['https://creativecommons.org/licenses/by/4.0/']
    attribution: Text
    membership_basis: Literal['owner_attestation', 'upstream_hash_match']
    membership_reference: Text
    original_filename: Annotated[str, Field(min_length=1, max_length=200)] | None
    local_filename: Annotated[str, Field(min_length=1, max_length=200)]
    upstream_image_sha256: Annotated[str, Field(pattern='^[0-9a-f]{64}$')] | None
    rename_statement_reference: Text | None
    laterality_evidence_reference: Text
    patient_grouping: Literal['isolated_demo_record', 'documented_same_patient']
    patient_grouping_reference: Text

    @model_validator(mode='after')
    def evidence_consistency(self):
        if self.membership_basis == 'upstream_hash_match' and self.upstream_image_sha256 is None:
            raise ValueError('Upstream hash evidence is required')
        for value in (self.attribution, self.membership_reference, self.laterality_evidence_reference,
                      self.patient_grouping_reference):
            if not value.strip():
                raise ValueError('Evidence text must not be empty')
        for value in (self.local_filename, self.original_filename):
            if value is not None and ('/' in value or '\\' in value or value in {'.', '..'}):
                raise ValueError('Only an image filename is accepted')
        return self
