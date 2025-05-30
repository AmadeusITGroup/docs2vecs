from typing import List, Optional
from tspii.reversible_anonymizers.reversible_anonymizer import ReversibleAnonymizer
from tspii.recognizers.recognizers import create_travel_specific_recognizers
from tspii.operators.faker_operators import create_fake_data_operators
from docs2vecs.subcommands.indexer.config import Config
from docs2vecs.subcommands.indexer.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill


class AnonymizerSkill(IndexerSkill):
    def __init__(self, skill_config: dict, global_config: Config) -> None:
        super().__init__(skill_config, global_config)
        self.usePlaceholders = self._config.get("use_placeholders", True)

    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        if not input:
            self.logger.info(f"No documents to anonymize")
            return input

        for document in input:
            reversible_anonymizer = ReversibleAnonymizer()

            # Add recognizers
            for recognizer in create_travel_specific_recognizers():
                reversible_anonymizer.add_recognizer(recognizer)

            if not self.usePlaceholders:
                # Add fake data operators
                reversible_anonymizer.add_operators(create_fake_data_operators())

            # Analyze and anonymize the text
            reversible_anonymizer.analyze(document.text)
            if reversible_anonymizer._analyzer_results:
                self.logger.info(
                    f"Found {len(reversible_anonymizer._analyzer_results)} entities to anonymize in the current document ({document.filename})."
                )
                result = reversible_anonymizer.anonymize()
                document.text = result.text
            else:
                self.logger.info(
                    f"No entities to anonymize found in the current document ({document.filename})."
                )

        self.logger.info(f"Successfully anonymized {len(input)} documents")
        return input
