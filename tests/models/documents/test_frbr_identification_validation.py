from lxml import etree

from caselawclient.models.documents.body_metadata.frbr_identification_validation import (
    frbr_identification_validation_failure,
    is_valid_frbr_identification,
)
from caselawclient.xml_helpers import DEFAULT_NAMESPACES

AKN_NS = DEFAULT_NAMESPACES["akn"]
UK_NS = DEFAULT_NAMESPACES["uk"]


def _identification(xml: str) -> etree._Element:
    root = etree.fromstring(xml.encode())
    node = root.xpath("//akn:identification", namespaces=DEFAULT_NAMESPACES)[0]
    return node


def _akn_child(parent: etree._Element, local_name: str) -> etree._Element:
    child = parent.find(f"{{{AKN_NS}}}{local_name}")
    assert child is not None
    return child


def _valid_identification() -> etree._Element:
    return _identification(
        """
        <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
          <judgment><meta><identification source="#tna">
            <FRBRWork>
              <FRBRthis value="https://example/id/work"/>
              <FRBRuri value="https://example/id/work"/>
              <FRBRdate date="2023-01-01" name="judgment"/>
              <FRBRauthor href="#tna"/>
              <FRBRcountry value="GB-UKM"/>
            </FRBRWork>
            <FRBRExpression>
              <FRBRthis value="https://example/expression"/>
              <FRBRuri value="https://example/expression"/>
              <FRBRdate date="2023-01-01" name="judgment"/>
              <FRBRauthor href="#tna"/>
              <FRBRlanguage language="eng"/>
            </FRBRExpression>
            <FRBRManifestation>
              <FRBRthis value="https://example/data.xml"/>
              <FRBRuri value="https://example/data.xml"/>
              <FRBRdate date="2023-01-01" name="judgment"/>
              <FRBRauthor href="#tna"/>
              <FRBRformat value="application/xml"/>
            </FRBRManifestation>
          </identification></meta></judgment>
        </akomaNtoso>
        """
    )


class TestFrbrIdentificationValidation:
    def test_valid_triple_passes(self):
        identification = _valid_identification()

        assert is_valid_frbr_identification(identification)
        assert frbr_identification_validation_failure(identification) is None

    def test_work_only_identification_fails(self):
        identification = _identification(
            """
            <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
              <judgment><meta><identification source="#tna">
                <FRBRWork>
                  <FRBRname value="Schema-invalid fixture"/>
                </FRBRWork>
              </identification></meta></judgment>
            </akomaNtoso>
            """
        )

        reason = frbr_identification_validation_failure(identification)
        assert reason is not None
        assert "FRBRExpression" in reason

    def test_rejects_non_identification_node(self):
        identification = _valid_identification()
        work = identification[0]

        reason = frbr_identification_validation_failure(work)

        assert reason == "node is not an identification element"

    def test_rejects_identification_in_wrong_namespace(self):
        identification = etree.Element(f"{{{UK_NS}}}identification", source="#tna")

        reason = frbr_identification_validation_failure(identification)

        assert reason == "identification is not in the Akoma Ntoso namespace"

    def test_rejects_missing_source_attribute(self):
        identification = _valid_identification()
        identification.attrib.pop("source")

        reason = frbr_identification_validation_failure(identification)

        assert reason == "identification is missing a source attribute"

    def test_rejects_missing_frbrwork(self):
        identification = _valid_identification()
        identification.remove(_akn_child(identification, "FRBRWork"))

        reason = frbr_identification_validation_failure(identification)

        assert reason == "identification is missing FRBRWork"

    def test_rejects_missing_frbrmanifestation(self):
        identification = _valid_identification()
        identification.remove(_akn_child(identification, "FRBRManifestation"))

        reason = frbr_identification_validation_failure(identification)

        assert reason == "identification is missing FRBRManifestation"

    def test_rejects_unexpected_identification_child(self):
        identification = _valid_identification()
        etree.SubElement(identification, f"{{{AKN_NS}}}lifecycle")

        reason = frbr_identification_validation_failure(identification)

        assert reason is not None
        assert "unexpected children" in reason
        assert "lifecycle" in reason

    def test_rejects_missing_required_work_child(self):
        identification = _valid_identification()
        work = _akn_child(identification, "FRBRWork")
        work.remove(_akn_child(work, "FRBRcountry"))

        reason = frbr_identification_validation_failure(identification)

        assert reason == "FRBRWork is missing FRBRcountry"

    def test_rejects_missing_expression_language(self):
        identification = _valid_identification()
        expression = _akn_child(identification, "FRBRExpression")
        expression.remove(_akn_child(expression, "FRBRlanguage"))

        reason = frbr_identification_validation_failure(identification)

        assert reason == "FRBRExpression is missing FRBRlanguage"

    def test_rejects_missing_manifestation_format(self):
        identification = _valid_identification()
        manifestation = _akn_child(identification, "FRBRManifestation")
        manifestation.remove(_akn_child(manifestation, "FRBRformat"))

        reason = frbr_identification_validation_failure(identification)

        assert reason == "FRBRManifestation is missing FRBRformat"

    def test_rejects_empty_frbrthis_value(self):
        identification = _valid_identification()
        work = _akn_child(identification, "FRBRWork")
        _akn_child(work, "FRBRthis").set("value", "   ")

        reason = frbr_identification_validation_failure(identification)

        assert reason == "FRBRWork/FRBRthis is missing a value attribute"

    def test_rejects_missing_frbrauthor_href(self):
        identification = _valid_identification()
        work = _akn_child(identification, "FRBRWork")
        _akn_child(work, "FRBRauthor").attrib.pop("href")

        reason = frbr_identification_validation_failure(identification)

        assert reason == "FRBRWork/FRBRauthor is missing an href attribute"

    def test_rejects_missing_decision_frbrdate(self):
        identification = _valid_identification()
        work = _akn_child(identification, "FRBRWork")
        work.remove(_akn_child(work, "FRBRdate"))

        reason = frbr_identification_validation_failure(identification)

        assert reason == "FRBRWork is missing FRBRdate"

    def test_rejects_empty_decision_frbrdate(self):
        identification = _valid_identification()
        work = _akn_child(identification, "FRBRWork")
        _akn_child(work, "FRBRdate").set("date", "")

        reason = frbr_identification_validation_failure(identification)

        assert reason == "FRBRWork/FRBRdate is missing a date attribute"

    def test_rejects_duplicate_frbrname_on_work(self):
        identification = _valid_identification()
        work = _akn_child(identification, "FRBRWork")
        etree.SubElement(work, f"{{{AKN_NS}}}FRBRname", value="first")
        etree.SubElement(work, f"{{{AKN_NS}}}FRBRname", value="second")

        reason = frbr_identification_validation_failure(identification)

        assert reason == "FRBRWork has multiple FRBRname elements"

    def test_rejects_unexpected_child_under_work(self):
        identification = _valid_identification()
        work = _akn_child(identification, "FRBRWork")
        etree.SubElement(work, f"{{{AKN_NS}}}NotInSchema")

        reason = frbr_identification_validation_failure(identification)

        assert reason == "FRBRWork has unexpected child NotInSchema"

    def test_rejects_empty_expression_language(self):
        identification = _valid_identification()
        expression = _akn_child(identification, "FRBRExpression")
        _akn_child(expression, "FRBRlanguage").set("language", "  ")

        reason = frbr_identification_validation_failure(identification)

        assert reason == "FRBRExpression/FRBRlanguage is missing a language attribute"

    def test_rejects_non_akn_child_under_work(self):
        identification = _valid_identification()
        work = _akn_child(identification, "FRBRWork")
        work.insert(0, etree.Element("{http://example.com/ns}foreign"))

        reason = frbr_identification_validation_failure(identification)

        assert reason == "FRBRWork contains a non-AKN child"

    def test_rejects_out_of_order_work_children(self):
        identification = _valid_identification()
        work = _akn_child(identification, "FRBRWork")
        work.insert(0, etree.Element(f"{{{AKN_NS}}}FRBRname", value="Before FRBRthis"))

        reason = frbr_identification_validation_failure(identification)

        assert reason == "FRBRWork child elements are not in schema order"
