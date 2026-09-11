/*
 * RelativePathsTest.cpp
 *
 * Copyright (c) 2017 Tres Finocchiaro <tres/dot/finocchiaro/at/gmail.com>
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

#include <QObject>
#include <QtTest>
#include <QTemporaryDir>

#include "ConfigManager.h"
#include "PathUtil.h"

class RelativePathsTest : public QObject
{
	Q_OBJECT
private:
	QTemporaryDir m_factoryData;
	QStringList m_originalSearchPaths;

private slots:
	void initTestCase()
	{
		QVERIFY(m_factoryData.isValid());
		lmms::ConfigManager::inst();
		m_originalSearchPaths = QDir::searchPaths("data");
		QVERIFY(QDir(m_factoryData.path()).mkpath("samples/drums"));
		QDir::setSearchPaths("data", {m_factoryData.path()});
	}

	void cleanupTestCase()
	{
		QDir::setSearchPaths("data", m_originalSearchPaths);
	}

	void PathUtilComparisonTests_data()
	{
		QTest::addColumn<QString>("oldRelPath");
		QTest::newRow("ascii") << QStringLiteral("drums/kick01.ogg");
		QTest::newRow("unicode") << QString::fromUtf8("drums/音符-é.ogg");
	}

	void PathUtilComparisonTests()
	{
		using namespace lmms;
		QFETCH(QString, oldRelPath);
		QFile fixture(m_factoryData.filePath("samples/" + oldRelPath));
		QVERIFY(fixture.open(QIODevice::WriteOnly | QIODevice::NewOnly));
		const QByteArray contents("Temporary path fixture; not audio.");
		QCOMPARE(fixture.write(contents), contents.size());
		fixture.close();

		QFileInfo fi(ConfigManager::inst()->factorySamplesDir() + oldRelPath);
		QVERIFY(fi.exists());

		QString absPath = fi.absoluteFilePath();
		QString relPath = PathUtil::basePrefix(PathUtil::Base::FactorySample) + oldRelPath;
		QString fuzPath = absPath;
		fuzPath.replace(relPath, "drums/.///kick01.ogg");

		//Test nicely formatted paths
		QCOMPARE(PathUtil::toShortestRelative(absPath), relPath);
		QCOMPARE(PathUtil::toAbsolute(relPath), absPath);

		//Test upgrading old paths
		QCOMPARE(PathUtil::toShortestRelative(oldRelPath), relPath);
		QCOMPARE(PathUtil::toAbsolute(oldRelPath), absPath);

		//Test weird but valid paths
		QCOMPARE(PathUtil::toShortestRelative(fuzPath), relPath);
		QCOMPARE(PathUtil::toAbsolute(fuzPath), absPath);

		//Empty paths should stay empty
		QString empty = QString("");
		QCOMPARE(PathUtil::stripPrefix(""), empty);
		QCOMPARE(PathUtil::cleanName(""), empty);
		QCOMPARE(PathUtil::toAbsolute(""), empty);
		QCOMPARE(PathUtil::toShortestRelative(""), empty);
	}
};

QTEST_GUILESS_MAIN(RelativePathsTest)
#include "RelativePathsTest.moc"
