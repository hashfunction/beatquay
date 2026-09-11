// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include "ExportFileIdentity.h"
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QTemporaryDir>
#ifdef Q_OS_WIN
#include <windows.h>
#include <io.h>
#else
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#ifdef Q_OS_LINUX
#include <sys/syscall.h>
#include <linux/fs.h>
#endif
#ifdef Q_OS_MACOS
#include <stdio.h>
#endif
#endif

namespace lmms
{
namespace
{
#ifdef Q_OS_WIN
std::optional<ExportFileIdentity> identityForHandle(HANDLE handle)
{
	FILE_ID_INFO info{};
	FILE_ATTRIBUTE_TAG_INFO attributes{};
	if (!GetFileInformationByHandleEx(handle, FileIdInfo, &info, static_cast<DWORD>(sizeof(info)))
		|| !GetFileInformationByHandleEx(handle, FileAttributeTagInfo, &attributes, static_cast<DWORD>(sizeof(attributes)))
		|| (attributes.FileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT))) { return {}; }
	return ExportFileIdentity{info.VolumeSerialNumber,
		QByteArray(reinterpret_cast<const char*>(info.FileId.Identifier), sizeof(info.FileId.Identifier))};
}
#else
std::optional<ExportFileIdentity> identityForStat(const struct stat& info)
{
	if (!S_ISREG(info.st_mode)) { return {}; }
	const auto inode = static_cast<quint64>(info.st_ino);
	return ExportFileIdentity{static_cast<quint64>(info.st_dev),
		QByteArray(reinterpret_cast<const char*>(&inode), sizeof(inode))};
}
#endif
} // namespace

std::optional<ExportFileIdentity> exportFileIdentity(int descriptor)
{
	if (descriptor < 0) { return {}; }
#ifdef Q_OS_WIN
	return identityForHandle(reinterpret_cast<HANDLE>(_get_osfhandle(descriptor)));
#else
	struct stat info{};
	if (fstat(descriptor, &info) != 0) { return {}; }
	return identityForStat(info);
#endif
}

std::optional<ExportFileIdentity> exportFileIdentity(const QString& path)
{
#ifdef Q_OS_WIN
	const auto handle = CreateFileW(reinterpret_cast<LPCWSTR>(path.utf16()), FILE_READ_ATTRIBUTES,
		FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING,
		FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
	if (handle == INVALID_HANDLE_VALUE) { return {}; }
	const auto identity = identityForHandle(handle);
	CloseHandle(handle);
	return identity;
#else
	struct stat info{};
	if (lstat(QFile::encodeName(path).constData(), &info) != 0) { return {}; }
	return identityForStat(info);
#endif
}

bool moveExportFileNoReplace(const QString& source, const QString& destination)
{
#ifdef Q_OS_WIN
	return MoveFileExW(reinterpret_cast<LPCWSTR>(source.utf16()),
		reinterpret_cast<LPCWSTR>(destination.utf16()), 0) != 0;
#elif defined(Q_OS_MACOS)
	return renamex_np(QFile::encodeName(source).constData(), QFile::encodeName(destination).constData(), RENAME_EXCL) == 0;
#elif defined(Q_OS_LINUX)
	return syscall(SYS_renameat2, AT_FDCWD, QFile::encodeName(source).constData(),
		AT_FDCWD, QFile::encodeName(destination).constData(), RENAME_NOREPLACE) == 0;
#else
	Q_UNUSED(source)
	Q_UNUSED(destination)
	return false; // No destructive or copy/delete fallback on unsupported systems.
#endif
}

bool removeOwnedExportFile(const QString& path, const ExportFileIdentity& identity, QString* recoveryPath)
{
	if (exportFileIdentity(path) != identity) { return false; }
#ifdef Q_OS_WIN
	// Exclude rename/delete while ownership is checked, then delete via this
	// very handle. There is no pathname re-open between comparison and deletion.
	const auto handle = CreateFileW(reinterpret_cast<LPCWSTR>(path.utf16()), DELETE | FILE_READ_ATTRIBUTES,
		FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
	if (handle == INVALID_HANDLE_VALUE) { return false; }
	FILE_DISPOSITION_INFO disposition{TRUE};
	const bool removed = identityForHandle(handle) == identity
		&& SetFileInformationByHandle(handle, FileDispositionInfo, &disposition, static_cast<DWORD>(sizeof(disposition)));
	CloseHandle(handle);
	Q_UNUSED(recoveryPath)
	return removed;
#else
	QTemporaryDir quarantine(QFileInfo(path).absolutePath() + "/.beatquay-cleanup-XXXXXX");
	if (!quarantine.isValid()) { return false; }
	quarantine.setAutoRemove(false);
	const auto displaced = quarantine.filePath("partial");
	if (!moveExportFileNoReplace(path, displaced))
	{
		QDir().rmdir(quarantine.path());
		return false;
	}
	if (exportFileIdentity(displaced) != identity)
	{
		if (!moveExportFileNoReplace(displaced, path) && recoveryPath) { *recoveryPath = displaced; }
		QDir().rmdir(quarantine.path());
		return false;
	}
	const bool removed = QFile::remove(displaced);
	if (!removed && recoveryPath) { *recoveryPath = displaced; }
	QDir().rmdir(quarantine.path()); // Empty-only: never delete unknown entries.
	return removed;
#endif
}
} // namespace lmms
