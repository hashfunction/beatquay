// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include "ProjectExportCheckDialog.h"
#include <QCoreApplication>
#include <QDialog>
#include <QDialogButtonBox>
#include <QLabel>
#include <QPlainTextEdit>
#include <QPushButton>
#include <QVBoxLayout>
#include <algorithm>

namespace lmms::gui
{
namespace
{
QString text(const char* value) { return QCoreApplication::translate("ProjectExportCheck", value); }
QString details(const QList<ProjectExportIssue>& issues)
{
	QStringList lines;
	for (const auto& issue : issues)
	{
		lines << issue.message;
		if (!issue.path.isEmpty()) { lines << issue.path; }
		lines << issue.recoveryAction << QString{};
	}
	return lines.join('\n');
}
int display(const QString& title, const QString& summary, const QString& detail, const QString& action, QWidget* parent)
{
	QDialog dialog(parent);
	dialog.setObjectName("ProjectExportCheckDialog");
	dialog.setWindowTitle(title);
	auto* layout = new QVBoxLayout(&dialog);
	auto* label = new QLabel(summary);
	label->setTextFormat(Qt::PlainText);
	label->setWordWrap(true);
	layout->addWidget(label);
	auto* body = new QPlainTextEdit;
	body->setObjectName("ExportCheckDetails");
	body->setReadOnly(true);
	body->setPlainText(detail);
	layout->addWidget(body);
	auto* buttons = new QDialogButtonBox;
	if (!action.isEmpty())
	{
		auto* proceed = buttons->addButton(action, QDialogButtonBox::AcceptRole);
		proceed->setObjectName("ContinueExportButton");
		proceed->setAutoDefault(false);
		auto* cancel = buttons->addButton(QDialogButtonBox::Cancel);
		cancel->setDefault(true);
		QObject::connect(buttons, &QDialogButtonBox::accepted, &dialog, &QDialog::accept);
	}
	else { buttons->addButton(QDialogButtonBox::Close); }
	QObject::connect(buttons, &QDialogButtonBox::rejected, &dialog, &QDialog::reject);
	layout->addWidget(buttons);
	dialog.resize(640, 420);
	return dialog.exec();
}
}
bool ProjectExportCheckDialog::confirm(const QList<ProjectExportIssue>& issues, QWidget* parent)
{
	if (issues.isEmpty()) { return true; }
	const bool errors = std::any_of(issues.begin(), issues.end(), [](const auto& issue)
	{ return issue.severity == ProjectExportIssue::Severity::Error; });
	const bool replacing = std::any_of(issues.begin(), issues.end(), [](const auto& issue)
	{ return issue.code == ProjectExportIssue::Code::ExistingDestination; });
	const auto summary = errors ? text("Resolve these issues before exporting.")
		: replacing ? text("Existing output files will be replaced. Their previous versions will be kept for recovery.")
		: text("Review these warnings before exporting.");
	const auto action = errors ? QString{} : replacing ? text("Replace and export") : text("Continue export");
	return display(text("Check export"), summary, details(issues), action, parent) == QDialog::Accepted && !errors;
}
void ProjectExportCheckDialog::showResult(const RenderResult& result, const QList<ProjectExportIssue>& issues, QWidget* parent)
{
	QStringList lines;
	if (!result.error.isEmpty()) { lines << result.error << QString{}; }
	for (const auto& output : result.outputs)
	{
		lines << output.path;
		if (output.status == RenderStatus::Succeeded) { lines << text("Completed: %1 bytes").arg(output.bytes); }
		else if (output.status == RenderStatus::Cancelled) { lines << text("Cancelled"); }
		else { lines << text("Failed"); }
		if (!output.error.isEmpty()) { lines << output.error; }
		if (!output.previousOutputPath.isEmpty()) { lines << text("Previous output preserved at:") << output.previousOutputPath; }
		if (!output.retainedPartialPath.isEmpty()) { lines << text("Retained render or staging entry:") << output.retainedPartialPath; }
		if (!output.cleanupRecoveryPath.isEmpty()) { lines << text("Cleanup recovery file:") << output.cleanupRecoveryPath; }
		lines << QString{};
	}
	lines << details(issues);
	const auto title = result.status == RenderStatus::Succeeded ? text("Export completed")
		: result.status == RenderStatus::Cancelled ? text("Export cancelled") : text("Export failed");
	display(title, title, lines.join('\n'), {}, parent);
}
}
