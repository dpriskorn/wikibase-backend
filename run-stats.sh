echo "# Overall" > statistics.md
printf '```\n' >> statistics.md
scc --no-cocomo --exclude-dir mediawiki-extensions-Wikibase --exclude-dir test_data --exclude-dir disabled_tests >> statistics.md
printf '```\n' >> statistics.md
echo "# src" >> statistics.md
printf '```\n' >> statistics.md
scc --no-cocomo src >> statistics.md
printf '```\n' >> statistics.md
echo "# src/models" >> statistics.md
printf '```\n' >> statistics.md
scc --no-cocomo src/models >> statistics.md
printf '```\n' >> statistics.md
echo "# src/models/entity_api" >> statistics.md
printf '```\n' >> statistics.md
scc --no-cocomo src/models/entity_api >> statistics.md
printf '```\n' >> statistics.md
echo "# src/models/infrastructure" >> statistics.md
printf '```\n' >> statistics.md
scc --no-cocomo src/models/infrastructure >> statistics.md
printf '```\n' >> statistics.md
echo "# src/models/internal_representation" >> statistics.md
printf '```\n' >> statistics.md
scc --no-cocomo src/models/internal_representation >> statistics.md
printf '```\n' >> statistics.md
echo "# src/models/json_parser" >> statistics.md
printf '```\n' >> statistics.md
scc --no-cocomo src/models/json_parser >> statistics.md
printf '```\n' >> statistics.md
echo "# src/models/rdf_builder" >> statistics.md
printf '```\n' >> statistics.md
scc --no-cocomo src/models/rdf_builder >> statistics.md
printf '```\n' >> statistics.md
