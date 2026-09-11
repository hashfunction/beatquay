// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#ifndef LMMS_PROJECT_EXPORT_SESSION_H
#define LMMS_PROJECT_EXPORT_SESSION_H
#include "ProjectExportCheck.h"
#include "ExportOutputPublication.h"
#include "RenderResult.h"
#include <functional>
namespace lmms
{
// The GUI's actual one-attempt decision boundary. The callback constructs the
// renderer only after errors, warning consent and snapshot revalidation pass.
class LMMS_EXPORT ProjectExportSession
{
public:
	enum class Decision { Continue, Cancel };
	using StartRenderer = std::function<void(const QList<ExportDestinationSnapshot>&, const QStringList&)>;
	ProjectExportSession(QList<ProjectExportFacts> facts, QStringList protectedPaths = {});
	const QList<ProjectExportIssue>& issues() const { return m_issues; }
	bool hasErrors() const;
	bool start(Decision decision, const StartRenderer& renderer);
	QList<ProjectExportIssue> postflight(RenderResult& result) const;
private:
	QList<ProjectExportFacts> m_facts;
	QStringList m_protectedPaths;
	QList<ExportDestinationSnapshot> m_destinations;
	QList<ProjectExportIssue> m_issues;
	bool m_decided = false;
	bool m_started = false;
};
} // namespace lmms
#endif
