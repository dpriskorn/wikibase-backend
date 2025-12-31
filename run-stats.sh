echo "# Overall" > STATISTICS.md
printf '```\n' >> STATISTICS.md
scc --no-cocomo --exclude-dir mediawiki-extensions-Wikibase --exclude-dir test_data --exclude-dir disabled_tests >> STATISTICS.md
printf '```\n' >> STATISTICS.md
echo "# src" >> STATISTICS.md
printf '```\n' >> STATISTICS.md
scc --no-cocomo src >> STATISTICS.md
printf '```\n' >> STATISTICS.md
echo "# src/models" >> STATISTICS.md
printf '```\n' >> STATISTICS.md
scc --no-cocomo src/models >> STATISTICS.md
printf '```\n' >> STATISTICS.md
echo "# src/models/entity_api" >> STATISTICS.md
printf '```\n' >> STATISTICS.md
scc --no-cocomo src/models/entity_api >> STATISTICS.md
printf '```\n' >> STATISTICS.md
echo "# src/models/infrastructure" >> STATISTICS.md
printf '```\n' >> STATISTICS.md
scc --no-cocomo src/models/infrastructure >> STATISTICS.md
printf '```\n' >> STATISTICS.md
echo "# src/models/internal_representation" >> STATISTICS.md
printf '```\n' >> STATISTICS.md
scc --no-cocomo src/models/internal_representation >> STATISTICS.md
printf '```\n' >> STATISTICS.md
echo "# src/models/json_parser" >> STATISTICS.md
printf '```\n' >> STATISTICS.md
scc --no-cocomo src/models/json_parser >> STATISTICS.md
printf '```\n' >> STATISTICS.md
echo "# src/models/rdf_builder" >> STATISTICS.md
printf '```\n' >> STATISTICS.md
scc --no-cocomo src/models/rdf_builder >> STATISTICS.md
printf '```\n' >> STATISTICS.md
