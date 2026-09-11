// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include "ExportOutputPublication.h"
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QTemporaryDir>

namespace lmms
{
namespace
{
QString message(const char* text) { return QCoreApplication::translate("ProjectExportCheck", text); }
bool sameFile(const ExportDestinationSnapshot& left, const ExportDestinationSnapshot& right)
{
	return left.exists == right.exists && left.identity == right.identity
		&& left.size == right.size && left.sha256 == right.sha256;
}
bool samePath(const QString& left, const QString& right)
{
#ifdef Q_OS_WIN
	return left.compare(right, Qt::CaseInsensitive) == 0;
#else
	return left == right;
#endif
}
bool hasEntry(const QString& path)
{
	const QFileInfo info(path);
	return info.exists() || info.isSymLink();
}
}

std::optional<ExportDestinationSnapshot> ExportDestinationSnapshot::capture(const QString& path, QString& error)
{
	error.clear();
	if (path.isEmpty()) { error = message("Choose an output file."); return {}; }
	ExportDestinationSnapshot result;
	result.path = QDir::cleanPath(QFileInfo(path).absoluteFilePath());
	result.exists = hasEntry(result.path);
	if (!result.exists) { return result; }
	result.identity = exportFileIdentity(result.path);
	if (!result.identity) { error = message("The output could not be identified as a regular file. Check access and choose a supported local destination."); return {}; }
	QFile file(result.path);
	if (!file.open(QIODevice::ReadOnly) || exportFileIdentity(file.handle()) != result.identity)
	{
		error = message("The output could not be read consistently. Check access and try again."); return {};
	}
	result.size = file.size();
	QCryptographicHash hash(QCryptographicHash::Sha256);
	if (!hash.addData(&file) || file.error() != QFileDevice::NoError
		|| file.size() != result.size || exportFileIdentity(result.path) != result.identity)
	{
		error = message("The output changed while it was checked. Choose it again."); return {};
	}
	result.sha256 = hash.result();
	return result;
}

ExportOutputPublication::ExportOutputPublication(ExportDestinationSnapshot destination, QStringList protectedPaths, Hook hook)
	: m_destination(std::move(destination)), m_protectedPaths(std::move(protectedPaths)), m_hook(std::move(hook)) {}

ExportOutputPublication::~ExportOutputPublication()
{
	if (m_retainFailedPublication) { return; }
	QString retained;
	discard(retained);
}

bool ExportOutputPublication::prepare(QString& error)
{
	if (m_staging || m_published) { error = message("This output has already been prepared."); return false; }
	for (const auto& protectedPath : m_protectedPaths)
	{
		if (samePath(QDir::cleanPath(QFileInfo(protectedPath).absoluteFilePath()), m_destination.path)
			|| (m_destination.identity && exportFileIdentity(QFileInfo(protectedPath).canonicalFilePath()) == m_destination.identity))
		{
			error = message("The destination is the project or one of its resources. Choose another file."); return false;
		}
	}
	const auto current = ExportDestinationSnapshot::capture(m_destination.path, error);
	if (!current || *current != m_destination)
	{
		if (error.isEmpty()) { error = message("The destination changed after confirmation. Choose it again."); }
		return false;
	}
	m_staging = std::make_unique<QTemporaryDir>(QFileInfo(m_destination.path).absolutePath() + "/.beatquay-render-XXXXXX");
	m_staging->setAutoRemove(false);
	if (!m_staging->isValid())
	{
		m_staging.reset(); error = message("A private render file could not be created beside the destination."); return false;
	}
	return true;
}

QString ExportOutputPublication::stagingPath() const
{
	return m_staging ? m_staging->filePath(QFileInfo(m_destination.path).fileName()) : QString{};
}

void ExportOutputPublication::claimOutput(const ExportFileIdentity& identity)
{
	// The renderer supplies the identity of its open descriptor, not a later
	// pathname observation. Never replace that capability after the first claim.
	if (!m_ownedIdentity) { m_ownedIdentity = identity; }
}

ExportPublicationResult ExportOutputPublication::publish()
{
	ExportPublicationResult result;
	result.path = m_destination.path;
	if (!m_staging || m_published)
	{
		result.error = message("This output is not awaiting publication."); return result;
	}
	m_retainFailedPublication = true;
	result.retainedPartialPath = stagingPath();
	QString error;
	const auto staged = ExportDestinationSnapshot::capture(stagingPath(), error);
	if (!staged || !staged->exists || !m_ownedIdentity || staged->identity != m_ownedIdentity || staged->size <= 0)
	{
		result.error = message("The finalized render is missing, empty or no longer owned by this export."); return result;
	}
	const auto current = ExportDestinationSnapshot::capture(m_destination.path, error);
	if (!current || *current != m_destination)
	{
		result.error = message("The destination changed after confirmation. The rendered file was preserved."); return result;
	}
	if (m_destination.exists)
	{
		QTemporaryDir previous(QFileInfo(m_destination.path).absolutePath() + "/.beatquay-previous-XXXXXX");
		previous.setAutoRemove(false);
		if (!previous.isValid())
		{
			result.error = message("The previous output could not be preserved. The destination was not replaced."); return result;
		}
		const auto backup = previous.filePath(QFileInfo(m_destination.path).fileName());
		if (m_hook) { m_hook(Checkpoint::BeforeDisplace); }
		if (!moveExportFileNoReplace(m_destination.path, backup))
		{
			QDir().rmdir(previous.path());
			result.error = message("The previous output could not be moved safely. The destination was not replaced."); return result;
		}
		result.previousOutputPath = backup;
		const auto displaced = ExportDestinationSnapshot::capture(backup, error);
		if (!displaced || !sameFile(*displaced, m_destination))
		{
			if (moveExportFileNoReplace(backup, m_destination.path))
			{
				result.previousOutputPath.clear(); QDir().rmdir(previous.path());
			}
			result.error = message("The destination changed during replacement. Its bytes were preserved; review the reported paths."); return result;
		}
		if (m_hook) { m_hook(Checkpoint::AfterDisplace); }
	}
	if (m_hook) { m_hook(Checkpoint::BeforePublish); }
	const auto beforeMove = ExportDestinationSnapshot::capture(stagingPath(), error);
	if (!beforeMove || *beforeMove != *staged || !moveExportFileNoReplace(stagingPath(), m_destination.path))
	{
		result.error = message("The output could not be published without replacing another file. Review the preserved paths."); return result;
	}
	const auto published = ExportDestinationSnapshot::capture(m_destination.path, error);
	if (!published || !sameFile(*published, *staged))
	{
		// A source substitution raced the move. Preserve it, restoring to its
		// staging name only if that name is still absent. Never overwrite either.
		if (!moveExportFileNoReplace(m_destination.path, stagingPath())) { result.retainedPartialPath = m_destination.path; }
		result.error = message("The output changed during publication. The observed file was preserved."); return result;
	}
	m_published = true;
	m_retainFailedPublication = false;
	result.published = true;
	result.bytes = published->size;
	result.retainedPartialPath.clear();
	if (!QDir().rmdir(m_staging->path())) { result.retainedPartialPath = m_staging->path(); }
	return result;
}

bool ExportOutputPublication::discard(QString& retainedPath)
{
	retainedPath.clear();
	if (!m_staging || m_published) { return true; }
	if (hasEntry(stagingPath()))
	{
		if (!m_ownedIdentity || !removeOwnedExportFile(stagingPath(), *m_ownedIdentity, &retainedPath))
		{
			if (retainedPath.isEmpty()) { retainedPath = stagingPath(); }
			return false;
		}
	}
	// An unknown file in our directory is never recursively removed.
	if (!QDir().rmdir(m_staging->path()) && QFileInfo::exists(m_staging->path()))
	{
		retainedPath = m_staging->path(); return false;
	}
	m_retainFailedPublication = false;
	return true;
}
} // namespace lmms
