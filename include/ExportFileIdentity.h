// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#ifndef LMMS_EXPORT_FILE_IDENTITY_H
#define LMMS_EXPORT_FILE_IDENTITY_H
#include <QByteArray>
#include <QString>
#include <optional>
#include "lmms_export.h"
namespace lmms
{
struct ExportFileIdentity
{
	quint64 volume = 0;
	QByteArray object;
	bool operator==(const ExportFileIdentity&) const = default;
};
LMMS_EXPORT std::optional<ExportFileIdentity> exportFileIdentity(int descriptor);
// Rejects nonregular files and leaf links/reparse points. Parent-directory
// substitution and hostile same-user filesystem mutation are outside this API.
LMMS_EXPORT std::optional<ExportFileIdentity> exportFileIdentity(const QString& path);
LMMS_EXPORT bool moveExportFileNoReplace(const QString& source, const QString& destination);
// Remove only the captured file. On a displacement/recovery failure, leave the
// file in place and report its exact recovery location; never recurse directories.
LMMS_EXPORT bool removeOwnedExportFile(const QString& path, const ExportFileIdentity& identity,
	QString* recoveryPath = nullptr);
} // namespace lmms
#endif
