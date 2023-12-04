import os

from unittest import TestCase, main

from ensembldb3.host import (
    DbConnection,
    HostAccount,
    get_db_name,
    get_ensembl_account,
    get_latest_release,
)
from ensembldb3.name import EnsemblDbName

from . import ENSEMBL_RELEASE


__author__ = "Gavin Huttley, Hua Ying"
__copyright__ = "Copyright 2016-, The EnsemblDb3 Project"
__credits__ = ["Gavin Huttley", "hua Ying"]
__license__ = "BSD"
__version__ = "2021.04.01"
__maintainer__ = "Gavin Huttley"
__email__ = "Gavin.Huttley@anu.edu.au"
__status__ = "alpha"

if "ENSEMBL_ACCOUNT" in os.environ:
    args = os.environ["ENSEMBL_ACCOUNT"].split()
    host, username, password = args[:3]
    kwargs = {}
    if len(args) > 3:
        kwargs["port"] = int(args[3])
    account = HostAccount(host, username, password, **kwargs)
else:
    account = get_ensembl_account(release=ENSEMBL_RELEASE)


class TestEnsemblDbName(TestCase):
    def test_cmp_name(self):
        """should validly compare names by attributes"""
        n1 = EnsemblDbName("homo_sapiens_core_46_36h")
        n2 = EnsemblDbName("homo_sapiens_core_46_36h")
        self.assertEqual(n1, n2)

    def test_name_without_build(self):
        """should correctly handle a db name without a build"""
        n = EnsemblDbName("pongo_pygmaeus_core_49_1")
        self.assertEqual(n.prefix, "pongo_pygmaeus")
        self.assertEqual(n.type, "core")
        self.assertEqual(n.build, "1")

    def test_species_with_three_words_name(self):
        """should correctly parse a db name that contains a three words species name"""
        n = EnsemblDbName("mustela_putorius_furo_core_70_1")
        self.assertEqual(n.prefix, "mustela_putorius_furo")
        self.assertEqual(n.type, "core")
        self.assertEqual(n.build, "1")
        self.assertEqual(n.species, "Mustela putorius furo")
        n = EnsemblDbName("canis_lupus_familiaris_core_102_31")
        self.assertEqual(n.species, "Canis lupus familiaris")

    def test_ensemblgenomes_names(self):
        """correctly handle the ensemblgenomes naming system"""
        n = EnsemblDbName("aedes_aegypti_core_5_58_1e")
        self.assertEqual(n.prefix, "aedes_aegypti")
        self.assertEqual(n.type, "core")
        self.assertEqual(n.release, "5")
        self.assertEqual(n.general_release, "58")
        self.assertEqual(n.build, "1e")
        n = EnsemblDbName("ensembl_compara_metazoa_6_59")
        self.assertEqual(n.release, "6")
        self.assertEqual(n.general_release, "59")
        self.assertEqual(n.type, "compara")


class TestHostAccount(TestCase):
    def test_host_comparison(self):
        """instances with same host, account, database, port are equal"""
        h1 = HostAccount("ensembldb.ensembl.org", "anonymous", "", port=5306)
        h2 = HostAccount("ensembldb.ensembl.org", "anonymous", "", port=5306)
        self.assertNotEqual(id(h1), id(h2))
        self.assertEqual(h1, h2)
        # hashes are also equal
        self.assertEqual(hash(h1), hash(h2))
        h3 = HostAccount("ensembldb.ensembl.org", "anonymous", "", port=5300)
        self.assertNotEqual(h1, h3)
        self.assertNotEqual(hash(h1), hash(h3))

    def test_account_str(self):
        """str"""
        h1 = HostAccount("ensembldb.ensembl.org", "anonymous", "", port=5306)
        self.assertEqual(str(h1), "user:passwd@ensembldb.ensembl.org:5306")
        self.assertEqual(h1.formatted(), "anonymous:@ensembldb.ensembl.org:5306")
        # default port, actual password
        h2 = HostAccount("mysql.host.org", "me", "tricky")
        self.assertEqual(str(h2), "user:passwd@mysql.host.org:3306")
        self.assertEqual(h2.formatted(), "me:tricky@mysql.host.org:3306")


class TestDBconnects(TestCase):
    def test_get_ensembl_account(self):
        """return an HostAccount with correct port"""
        for release in [48, "48", None]:
            act_new = get_ensembl_account(release=ENSEMBL_RELEASE)
            self.assertEqual(act_new.port, 5306)

        for release in [45, "45"]:
            act_old = get_ensembl_account(release=45)
            self.assertEqual(act_old.port, 3306)

    def test_getdb(self):
        """should discover human entries correctly"""
        for name, db_name in [
            ("human", "homo_sapiens_core_49_36k"),
            ("mouse", "mus_musculus_core_49_37b"),
            ("rat", "rattus_norvegicus_core_49_34s"),
            ("platypus", "ornithorhynchus_anatinus_core_49_1f"),
        ]:
            result = get_db_name(species=name, db_type="core", release="49")
            self.assertEqual(len(result), 1)
            result = result[0]
            self.assertEqual(result.name, db_name)
            self.assertEqual(result.release, "49")

    def test_latest_release_number(self):
        """should correctly identify the latest release number"""
        self.assertGreater(int(get_latest_release()), 53)

    def test_get_all_available(self):
        """should return a listing of all the available databases on the
        indicated server"""
        available = get_db_name()
        one_valid = any(db.type == "compara" for db in available)
        self.assertEqual(one_valid, True)
        # now check that when we request available under a specific version
        # that we only receive valid ones back
        available = get_db_name(release="46")
        for db in available:
            self.assertEqual(db.release, "46")

    def test_active_connections(self):
        """connecting to a database on a specified server should be done once
        only, but same database on a different server should be done"""
        ensembl_acct = get_ensembl_account(release="46")
        engine1 = DbConnection(account=ensembl_acct, db_name="homo_sapiens_core_46_36h")
        engine2 = DbConnection(account=ensembl_acct, db_name="homo_sapiens_core_46_36h")
        self.assertEqual(engine1, engine2)

    def test_pool_recycle_option(self):
        """excercising ability to specify a pool recycle option"""
        ensembl_acct = get_ensembl_account(release="56")
        engine1 = DbConnection(
            account=ensembl_acct, db_name="homo_sapiens_core_46_36h", pool_recycle=1000
        )


if __name__ == "__main__":
    main()
