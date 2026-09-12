/*
 * AboutDialog.cpp - implementation of about-dialog
 *
 * Copyright (c) 2004-2008 Tobias Doerffel <tobydox/at/users.sourceforge.net>
 *
 * This file is part of LMMS - https://lmms.io
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public
 * License along with this program (see COPYING); if not, write to the
 * Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
 * Boston, MA 02110-1301 USA.
 *
 */


#include "lmmsversion.h"
#include "BeatQuayIdentity.h"
#include "AboutDialog.h"
#include "embed.h"
#include "versioninfo.h"


namespace lmms::gui
{

AboutDialog::AboutDialog(QWidget* parent) :
	QDialog(parent),
	Ui::AboutDialog()
{
	setupUi( this );
	setWindowTitle(tr("About %1").arg(product::Name));
	label->setText(QString::fromLatin1(product::DisplayTitle));
	label_2->setText(tr("Music creation by %1. Based on LMMS, with the original authors credited below.")
		.arg(product::Publisher));
	label_4->setText(QString(R"(<a href="%1">%1</a> · <a href="%2">Privacy</a> · <a href="%3">Support</a><br>Upstream: <a href="https://lmms.io">LMMS</a>)")
		.arg(product::Website, product::Privacy, product::Support));
	label_4->setOpenExternalLinks(true);


	iconLabel->setPixmap( QPixmap(product::Icon).scaled(64, 64, Qt::KeepAspectRatio, Qt::SmoothTransformation) );

	versionLabel->setText( versionLabel->text().
					arg(product::Version).
					arg( LMMS_BUILDCONF_PLATFORM ).
					arg( LMMS_BUILDCONF_MACHINE ).
					arg( QT_VERSION_STR ).
					arg( LMMS_BUILDCONF_COMPILER_VERSION ) );
	versionLabel->setTextInteractionFlags(
					versionLabel->textInteractionFlags() |
					Qt::TextSelectableByMouse );

	copyrightLabel->setText( copyrightLabel->text().
					arg(QString::fromLatin1(LMMS_PROJECT_COPYRIGHT) + "; 2026 " + product::Publisher) );

	authorLabel->setPlainText( embed::getText( "AUTHORS" ) );

	licenseLabel->setPlainText( embed::getText( "COMBINED-LICENSE.md" ) + "\n\n"
		+ embed::getText( "GPL-3.0.txt" ) + "\n\n"
		+ tr("Original application license (preserved):") + "\n\n"
		+ embed::getText( "LICENSE.txt" ) );

	involvedLabel->setPlainText( embed::getText( "CONTRIBUTORS" ) );
}

} // namespace lmms::gui
