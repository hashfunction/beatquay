// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#ifndef LMMS_PROJECT_EXPORT_FACTS_COLLECTOR_H
#define LMMS_PROJECT_EXPORT_FACTS_COLLECTOR_H
#include "ProjectExportCheck.h"
#include <QStringList>
namespace lmms
{
struct CollectedProjectExportFacts
{
	QList<ProjectExportFacts> outputs;
	QStringList protectedPaths;
};
class LMMS_EXPORT ProjectExportFactsCollector
{
public:
	static CollectedProjectExportFacts collect(ProjectRenderer::ExportFileFormat format,
		const QStringList& outputPaths, bool betweenMarkers, bool exportLoop, int loopCount);
};
} // namespace lmms
#endif
