from datetime import UTC, datetime
from uuid import uuid4

from caselawclient.factories import PressSummaryFactory
from caselawclient.models.documents.body import DocumentBody
from caselawclient.models.documents.body_metadata import BodyMetadataWriteBack, writable_akn_document_root_xpath
from caselawclient.models.documents.body_metadata.akn import FRBR_WORK_XPATH
from caselawclient.models.documents.body_metadata.frbr_identification_writer import FrbrIdentificationWriter
from caselawclient.models.documents.metadata.fields.field import MetadataField, MetadataStringValue
from caselawclient.models.documents.metadata.fields.source import MetadataSource


class TestWritableAknDocumentRoot:
    def test_ambiguous_root_is_not_writable(self):
        body = DocumentBody(
            b"""<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
            <judgment name="judgment"><meta/></judgment>
            <doc name="pressSummary"><mainBody/></doc>
            </akomaNtoso>"""
        )
        assert writable_akn_document_root_xpath(body._xml) is None  # noqa: SLF001
        assert body.supports_metadata_write_back is False

    def test_judgment_and_doc_are_writable(self):
        judgment = DocumentBody(
            b"""<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
            <judgment name="judgment"><meta/></judgment></akomaNtoso>"""
        )
        doc = DocumentBody(
            b"""<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
            <doc name="pressSummary"><mainBody/></doc></akomaNtoso>"""
        )
        assert writable_akn_document_root_xpath(judgment._xml) is not None  # noqa: SLF001
        assert writable_akn_document_root_xpath(doc._xml) is not None  # noqa: SLF001

    def test_parser_error_is_not_writable(self):
        body = DocumentBody(b"<error>failed</error>")
        assert body.supports_metadata_write_back is False

    def test_sync_noops_when_body_is_not_writable(self, mock_api_client):
        body = DocumentBody(b"<error>failed</error>")
        document = PressSummaryFactory.build(api_client=mock_api_client, body=body)

        assert BodyMetadataWriteBack().sync(document) is False


class TestFrbrIdentificationWriter:
    def test_write_returns_false_when_body_is_not_writable(self, mock_api_client):
        document = PressSummaryFactory.build(
            api_client=mock_api_client,
            body=DocumentBody(b"<error>failed</error>"),
        )

        assert FrbrIdentificationWriter().write(document) is False

    def test_uses_decision_frbrdate_name_from_judgment_root(self, mock_api_client):
        body = DocumentBody(
            b"""
            <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
              <judgment name="decision">
                <meta>
                  <identification source="#tna">
                    <FRBRWork>
                      <FRBRthis value="https://example/id/work"/>
                      <FRBRuri value="https://example/id/work"/>
                      <FRBRdate date="2022-02-02" name="decision"/>
                      <FRBRauthor href="#tna"/>
                      <FRBRcountry value="GB-UKM"/>
                    </FRBRWork>
                    <FRBRExpression>
                      <FRBRthis value="https://example/expression"/>
                      <FRBRuri value="https://example/expression"/>
                      <FRBRdate date="2022-02-02" name="decision"/>
                      <FRBRauthor href="#tna"/>
                      <FRBRlanguage language="eng"/>
                    </FRBRExpression>
                    <FRBRManifestation>
                      <FRBRthis value="https://example/data.xml"/>
                      <FRBRuri value="https://example/data.xml"/>
                      <FRBRdate date="2022-02-02" name="decision"/>
                      <FRBRauthor href="#tna"/>
                      <FRBRformat value="application/xml"/>
                    </FRBRManifestation>
                  </identification>
                </meta>
                <header><p/></header>
                <judgmentBody><decision><p/></decision></judgmentBody>
              </judgment>
            </akomaNtoso>
            """
        )
        from caselawclient.factories import JudgmentFactory

        document = JudgmentFactory.build(api_client=mock_api_client, body=body)
        assert FrbrIdentificationWriter().write(document) is True
        assert (
            document.body.get_xpath_match_string(f"{FRBR_WORK_XPATH}/akn:FRBRdate[@name='decision']/@date")
            == "2022-02-02"
        )

    def test_scaffold_ignores_unparseable_existing_frbrdate(self, mock_api_client):
        body = DocumentBody(
            b"""
            <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
              <doc name="pressSummary">
                <meta>
                  <identification source="#tna">
                    <FRBRWork>
                      <FRBRthis value="https://example/id/work"/>
                      <FRBRuri value="https://example/id/work"/>
                      <FRBRdate date="not-a-date" name="judgment"/>
                      <FRBRauthor href="#tna"/>
                      <FRBRcountry value="GB-UKM"/>
                    </FRBRWork>
                  </identification>
                </meta>
                <mainBody><p/></mainBody>
              </doc>
            </akomaNtoso>
            """
        )
        document = PressSummaryFactory.build(api_client=mock_api_client, body=body)
        document.metadata_fields.add(
            MetadataField(
                name="title",
                value=MetadataStringValue("Title"),
                source=MetadataSource.EDITOR,
                id=str(uuid4()),
                timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            )
        )

        assert FrbrIdentificationWriter().write(document) is True
        assert (
            document.body.get_xpath_match_string(
                "/akn:akomaNtoso/akn:doc/akn:meta/akn:identification/akn:FRBRExpression"
                "/akn:FRBRdate[@name='judgment']/@date"
            )
            == "1001-01-01"
        )

    def test_creates_identification_triple_from_scratch(self, mock_api_client):
        body = DocumentBody(
            b"""<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
            <doc name="pressSummary"><mainBody><p/></mainBody></doc></akomaNtoso>"""
        )
        document = PressSummaryFactory.build(api_client=mock_api_client, body=body)
        document.metadata_fields.add(
            MetadataField(
                name="title",
                value=MetadataStringValue("Example title"),
                source=MetadataSource.EDITOR,
                id=str(uuid4()),
                timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            )
        )
        assert FrbrIdentificationWriter().write(document) is True
        assert (
            body.get_xpath_match_string(
                "/akn:akomaNtoso/akn:doc/akn:meta/akn:identification/akn:FRBRWork/akn:FRBRname/@value"
            )
            == "Example title"
        )
        assert body.get_xpath_match_string(
            "/akn:akomaNtoso/akn:doc/akn:meta/akn:identification/akn:FRBRWork/akn:FRBRthis/@value"
        ).endswith("/id/test/2023/123")

    def test_repairs_incomplete_identification_when_trial_block_is_valid(self, mock_api_client):
        from caselawclient.models.documents.body import DocumentBody

        body = DocumentBody(
            b"""
            <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
              <doc name="pressSummary">
                <meta>
                  <identification source="#tna">
                    <FRBRWork>
                      <FRBRname value="Broken"/>
                    </FRBRWork>
                  </identification>
                </meta>
                <mainBody><p/></mainBody>
              </doc>
            </akomaNtoso>
            """
        )
        document = PressSummaryFactory.build(api_client=mock_api_client, body=body)

        assert FrbrIdentificationWriter().write(document) is True
        assert body.get_xpath_nodes("/akn:akomaNtoso/akn:doc/akn:meta/akn:identification/akn:FRBRExpression")

    def test_does_not_commit_when_trial_identification_stays_invalid(self, mock_api_client, caplog):
        from caselawclient.models.documents.body import DocumentBody

        body = DocumentBody(
            b"""
            <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
              <doc name="pressSummary">
                <meta>
                  <identification source="#tna">
                    <FRBRWork>
                      <FRBRthis value="https://example/id/work"/>
                      <FRBRuri value="https://example/id/work"/>
                      <FRBRdate date="2023-01-01" name="judgment"/>
                      <FRBRauthor href="#tna"/>
                      <FRBRcountry value="GB-UKM"/>
                    </FRBRWork>
                    <lifecycle source="#tna"/>
                  </identification>
                </meta>
                <mainBody><p/></mainBody>
              </doc>
            </akomaNtoso>
            """
        )
        original_frbrname = body.get_xpath_match_string(
            "/akn:akomaNtoso/akn:doc/akn:meta/akn:identification/akn:FRBRWork/akn:FRBRname/@value"
        )
        document = PressSummaryFactory.build(api_client=mock_api_client, body=body)
        document.metadata_fields.add(
            MetadataField(
                name="title",
                value=MetadataStringValue("Editor title"),
                source=MetadataSource.EDITOR,
                id=str(uuid4()),
                timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            )
        )

        assert FrbrIdentificationWriter().write(document) is False
        assert (
            body.get_xpath_match_string(
                "/akn:akomaNtoso/akn:doc/akn:meta/akn:identification/akn:FRBRWork/akn:FRBRname/@value"
            )
            == original_frbrname
        )
        assert "unexpected children" in caplog.text

    def test_does_not_commit_when_identification_validator_rejects_trial(self, mock_api_client, caplog):
        from caselawclient.models.documents.body import DocumentBody

        body = DocumentBody(
            b"""
            <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
              <doc name="pressSummary"><mainBody><p/></mainBody></doc>
            </akomaNtoso>
            """
        )
        original_xml = body.content_as_xml
        document = PressSummaryFactory.build(api_client=mock_api_client, body=body)
        document.metadata_fields.add(
            MetadataField(
                name="title",
                value=MetadataStringValue("Example title"),
                source=MetadataSource.EDITOR,
                id=str(uuid4()),
                timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            )
        )

        def reject_identification(_identification):
            return "trial identification rejected"

        assert FrbrIdentificationWriter(identification_validator=reject_identification).write(document) is False
        assert body.content_as_xml == original_xml
        assert "trial identification rejected" in caplog.text
