// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#ifndef LMMS_EXPORT_OUTPUT_PUBLICATION_H
#define LMMS_EXPORT_OUTPUT_PUBLICATION_H
#include "ExportFileIdentity.h"
#include <functional>
#include <memory>
#include <QStringList>
class QTemporaryDir;
namespace lmms
{
struct LMMS_EXPORT ExportDestinationSnapshot
{
	QString path;
	bool exists = false;
	std::optional<ExportFileIdentity> identity;
	qint64 size = 0;
	QByteArray sha256;
	bool operator==(const ExportDestinationSnapshot&) const = default;
	static std::optional<ExportDestinationSnapshot> capture(const QString& path, QString& error);
};
struct ExportPublicationResult
{
	bool published = false;
	qint64 bytes = 0;
	QString path;
	QString previousOutputPath;
	QString retainedPartialPath;
	QString error;
};
class LMMS_EXPORT ExportOutputPublication
{
public:
	enum class Checkpoint { BeforeDisplace, AfterDisplace, BeforePublish };
	using Hook = std::function<void(Checkpoint)>;
	explicit ExportOutputPublication(ExportDestinationSnapshot destination, QStringList protectedPaths = {}, Hook hook = {});
	~ExportOutputPublication();
	bool prepare(QString& error);
	QString stagingPath() const;
	QString destinationPath() const { return m_destination.path; }
	void claimOutput(const ExportFileIdentity& identity);
	ExportPublicationResult publish();
	bool discard(QString& retainedPath);
private:
	ExportDestinationSnapshot m_destination;
	QStringList m_protectedPaths;
	Hook m_hook;
	std::unique_ptr<QTemporaryDir> m_staging;
	std::optional<ExportFileIdentity> m_ownedIdentity;
	bool m_published = false;
	bool m_retainFailedPublication = false;
};
} // namespace lmms
#endif
