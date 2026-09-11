// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include "ProjectExportSession.h"
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QSet>
#include <algorithm>

namespace lmms
{
namespace
{
using Code = ProjectExportIssue::Code;
using Severity = ProjectExportIssue::Severity;
ProjectExportIssue failure(Code code, const QString& path, const QString& text)
{
	return {code, Severity::Error, path, text,
		QCoreApplication::translate("ProjectExportCheck", "Review the reported paths and check the export again.")};
}
QString message(const char* text) { return QCoreApplication::translate("ProjectExportCheck", text); }
QString normalized(const QString& path)
{
	const auto absolute = QDir::cleanPath(QFileInfo(path).absoluteFilePath());
#ifdef Q_OS_WIN
	return absolute.toCaseFolded();
#else
	return absolute;
#endif
}
}

ProjectExportSession::ProjectExportSession(QList<ProjectExportFacts> facts, QStringList protectedPaths)
	: m_facts(std::move(facts)), m_protectedPaths(std::move(protectedPaths))
{
	QSet<QString> paths;
	if (m_facts.isEmpty())
	{
		m_issues.append(failure(Code::EmptyProject, {}, message("No renderable outputs were selected.")));
	}
	for (auto& fact : m_facts)
	{
		QString error;
		const auto snapshot = ExportDestinationSnapshot::capture(fact.outputPath, error);
		if (snapshot)
		{
			fact.outputPath = snapshot->path;
			fact.outputExists = snapshot->exists;
			fact.outputIsRegularFile = snapshot->identity.has_value();
			fact.outputReadable = snapshot->exists;
			fact.outputWritable = QFileInfo(snapshot->path).isWritable();
			fact.outputSize = snapshot->size;
			m_destinations.append(*snapshot);
			for (const auto& protectedPath : m_protectedPaths)
			{
				if (normalized(protectedPath) == normalized(snapshot->path)
					|| (snapshot->identity && exportFileIdentity(QFileInfo(protectedPath).canonicalFilePath()) == snapshot->identity))
				{
					m_issues.append(failure(Code::OutputNotWritable, snapshot->path,
						message("The destination is the project or one of its resources. Choose another file.")));
				}
			}
		}
		else { m_issues.append(failure(Code::OutputUnreadable, fact.outputPath, error)); }
		const auto path = normalized(fact.outputPath);
		if (paths.contains(path))
		{
			m_issues.append(failure(Code::OutputNotWritable, fact.outputPath, message("More than one render uses this destination.")));
		}
		paths.insert(path);
		m_issues.append(ProjectExportCheck::beforeExport(fact));
	}
	std::stable_sort(m_issues.begin(), m_issues.end(), [](const auto& left, const auto& right)
	{ return left.severity < right.severity; });
}

bool ProjectExportSession::hasErrors() const
{
	return std::any_of(m_issues.begin(), m_issues.end(), [](const auto& issue) { return issue.severity == Severity::Error; });
}

bool ProjectExportSession::start(Decision decision, const StartRenderer& renderer)
{
	if (m_decided) { return false; }
	m_decided = true;
	if (decision != Decision::Continue || hasErrors()) { return false; }
	for (const auto& facts : m_facts)
	{
		for (const auto& resource : facts.resources)
		{
			QFile file(resource.path);
			if (!QFileInfo(resource.path).isFile() || !file.open(QIODevice::ReadOnly))
			{
				m_issues.append(failure(QFileInfo(resource.path).isFile() ? Code::UnreadableResource : Code::MissingResource,
					resource.path, message("A required resource is no longer available. Locate it and check again.")));
				return false;
			}
		}
	}
	for (const auto& destination : m_destinations)
	{
		QString error;
		const auto current = ExportDestinationSnapshot::capture(destination.path, error);
		if (!current || *current != destination)
		{
			m_issues.append(failure(Code::OutputNotWritable, destination.path,
				message("The destination changed after confirmation. Choose it again.")));
			return false;
		}
	}
	m_started = true;
	renderer(m_destinations, m_protectedPaths);
	return true;
}

QList<ProjectExportIssue> ProjectExportSession::postflight(RenderResult& result) const
{
	QList<ProjectExportIssue> issues;
	if (result.status == RenderStatus::Cancelled) { return issues; }
	if (!m_started)
	{
		issues.append(failure(Code::RenderNotCompleted, {}, message("This export was never started.")));
	}
	QSet<QString> expected;
	for (const auto& fact : m_facts) { expected.insert(normalized(fact.outputPath)); }
	QSet<QString> observed;
	for (auto& output : result.outputs)
	{
		const auto path = normalized(output.path);
		if (!expected.contains(path) || observed.contains(path))
		{
			issues.append(failure(Code::RenderNotCompleted, output.path, message("The renderer returned an unexpected or duplicate output.")));
			continue;
		}
		observed.insert(path);
		QFile file(output.path);
		ProjectExportFacts facts;
		facts.outputPath = output.path;
		facts.outputExists = QFileInfo::exists(output.path);
		facts.outputIsRegularFile = exportFileIdentity(output.path).has_value();
		facts.outputReadable = facts.outputIsRegularFile && file.open(QIODevice::ReadOnly);
		facts.outputSize = facts.outputReadable ? file.size() : 0;
		facts.renderCompleted = output.status == RenderStatus::Succeeded && output.encoderFinalized;
		const auto outputIssues = ProjectExportCheck::afterExport(facts);
		issues.append(outputIssues);
		if (outputIssues.isEmpty()) { output.bytes = facts.outputSize; }
		else { output.status = RenderStatus::Failed; }
	}
	for (const auto& fact : m_facts)
	{
		if (!observed.contains(normalized(fact.outputPath)))
		{
			issues.append(failure(Code::MissingOutput, fact.outputPath, message("The requested render has no completed output.")));
		}
	}
	if (result.status == RenderStatus::Failed && issues.isEmpty())
	{
		issues.append(failure(Code::RenderNotCompleted, {},
			result.error.isEmpty() ? message("Rendering did not complete successfully.") : result.error));
	}
	if (!issues.isEmpty()) { result.status = RenderStatus::Failed; }
	return issues;
}
} // namespace lmms
