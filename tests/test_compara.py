import os

from unittest import TestCase, main

from cogent3 import load_tree, make_tree
from numpy.testing import assert_allclose

from ensembldb3.compara import Compara
from ensembldb3.host import HostAccount, get_ensembl_account

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


def calc_slope(x1, y1, x2, y2):
    """computes the slope from two coordinate sets, assigning a delta of 1
    when values are identical"""
    delta_y = y2 - y1
    delta_x = x2 - x1
    delta_y = [delta_y, 1][delta_y == 0]
    delta_x = [delta_x, 1][delta_x == 0]
    return delta_y / delta_x


class ComparaTestBase(TestCase):
    comp = Compara(
        ["human", "mouse", "rat", "platypus"], release=ENSEMBL_RELEASE, account=account
    )
    eutheria = Compara(
        ["human", "mouse", "rat"], release=ENSEMBL_RELEASE, account=account
    )


class TestCompara(ComparaTestBase):
    def test_query_genome(self):
        """compara should attach valid genome attributes by common name"""
        brca2 = self.comp.Mouse.get_gene_by_stableid("ENSMUSG00000041147")
        self.assertEqual(brca2.symbol.lower(), "brca2")

    def test_get_related_genes(self):
        """should correctly return the related gene regions from each genome"""
        brca2 = self.comp.Mouse.get_gene_by_stableid("ENSMUSG00000041147")
        Orthologs = list(
            self.comp.get_related_genes(
                gene_region=brca2, relationship="ortholog_one2one"
            )
        )[0]
        self.assertEqual("ortholog_one2one", Orthologs.relationship)

    def test_get_related_genes2(self):
        """should handle case where gene is absent from one of the genomes"""
        clec2d = self.comp.Mouse.get_gene_by_stableid(stableid="ENSMUSG00000030157")
        orthologs = self.comp.get_related_genes(
            gene_region=clec2d, relationship="ortholog_one2many"
        )
        self.assertTrue(len(list(orthologs)[0].members) < 4)

    def test_get_related_genes3(self):
        """should get all relationships if relationship is not specified"""
        stableid = "ENSG00000244734"
        expect = {"within_species_paralog", "other_paralog"}
        orthologs = self.comp.get_related_genes(stableid=stableid)
        got = {ortholog.relationship for ortholog in orthologs}
        self.assertEqual(got, expect)

    def test_get_collection(self):
        brca2 = self.comp.Human.get_gene_by_stableid(stableid="ENSG00000139618")
        Orthologs = self.comp.get_related_genes(
            gene_region=brca2, relationship="ortholog_one2one"
        )
        collection = list(Orthologs)[0].get_seq_collection()
        self.assertTrue(len(collection.seqs[0]) > 1000)

    def test_getting_alignment(self):
        mid = "ENSMUSG00000017119"
        nbr1 = self.eutheria.Mouse.get_gene_by_stableid(stableid=mid)
        ## previous test gene mouse brca2 doesn't have alignment to other species using PECAN since release 86.
        results = list(
            self.eutheria.get_syntenic_regions(
                region=nbr1, align_method="PECAN", align_clade="vertebrates"
            )
        )
        # to improve test robustness across Ensembl releases, where alignment
        # coordinates change due to inclusion of new species, we search for
        # a mouse subseq and use the resulting coords to ensure we get the
        # same match as that from the Ensembl website
        aln = results[-1].get_alignment().to_type(array_align=True)
        mouse_name = [n for n in aln.names if n.startswith("Mus")][0]
        mouse_seq = str(aln.get_seq(mouse_name))
        start = mouse_seq.find("CTGCTGCTGACTTTCCG")

        sub_aln = aln[start : start + 17]
        seqs = list(sub_aln.to_dict().values())
        expect = {
            "ATGCTGATGACTTCTTT",  # human
            "CTGCTGCTGACTTTCCG",  # mouse
            "ATGCTGGTGACGTCTCG",  # rat
        }
        self.assertEqual(set(seqs), expect)
        self.assertTrue(len(aln) > 1000)

    def test_generate_method_clade_data(self):
        """should correctly determine the align_method align_clade options for
        a group of species"""
        # we should correctly infer the method_species_links, which is a
        # cogent3.util.Table instance
        self.assertTrue(self.comp.method_species_links.shape > (0, 0))

    def test_no_method_clade_data(self):
        """generate a Table with no rows if no alignment data"""
        compara = Compara(["S.cerevisiae"], release=ENSEMBL_RELEASE, account=account)
        self.assertEqual(compara.method_species_links.shape[0], 0)

    def test_get_syntenic_returns_nothing(self):
        """should correctly return None for a SyntenicRegion with golden-path
        assembly gap"""
        start = 100000
        end = start + 100000
        related = list(
            self.eutheria.get_syntenic_regions(
                species="mouse",
                coord_name="1",
                start=start,
                end=end,
                align_method="PECAN",
                align_clade="vertebrates",
            )
        )
        self.assertEqual(related, [])

    def test_get_species_set(self):
        """should return the correct set of species"""
        expect = {
            "Homo sapiens",
            "Mus musculus",
            "Rattus norvegicus",
            "Ornithorhynchus anatinus",
        }
        brca1 = self.comp.Human.get_gene_by_stableid(stableid="ENSG00000012048")
        orthologs = list(
            self.comp.get_related_genes(
                gene_region=brca1, relationship="ortholog_one2one"
            )
        )
        got = orthologs[0].get_species_set()
        self.assertEqual(got, expect)

    def test_gene_tree(self):
        """gene tree should match one downloaded from ensembl web"""
        hbb = self.comp.Human.get_gene_by_stableid("ENSG00000244734")
        paras = list(
            self.comp.get_related_genes(
                gene_region=hbb, relationship="within_species_paralog"
            )
        )
        t = paras[0].get_tree()
        expect = load_tree("data/HBB_gene_tree.nh")
        expect = expect.get_sub_tree(t.get_tip_names(), ignore_missing=True)
        self.assertTrue(expect.same_topology(t))

    def test_species_tree(self):
        """should match the one used by ensembl"""
        comp = Compara(
            ["human", "rat", "dog", "platypus"],
            release=ENSEMBL_RELEASE,
            account=account,
        )

        # sub-tree should have correct species
        sub_species = comp.get_species_tree(just_members=True)
        self.assertEqual(
            set(sub_species.get_tip_names()),
            {
                "Homo sapiens",
                "Rattus norvegicus",
                "Canis lupus familiaris",
                "Ornithorhynchus anatinus",
            },
        )
        # topology should match current topology belief
        expect = make_tree(
            treestring="(((Homo_sapiens,Rattus_norvegicus),"
            "Canis_lupus_familiaris),Ornithorhynchus_anatinus)",
            underscore_unmunge=True,
        )
        self.assertTrue(sub_species.same_topology(expect))

        # returned full tree should match download from ensembl
        # but taxon names are customised in what they put up on
        # the web-site, so need a better test.
        sptree = comp.get_species_tree(just_members=False)
        expect = load_tree("data/ensembl_all_species.nh", underscore_unmunge=True)
        self.assertTrue(len(sptree.get_tip_names()) > len(expect.get_tip_names()))

    def test_pool_connection(self):
        """excercising ability to specify pool connection"""
        dog = Compara(
            ["chimp", "dog"],
            release=ENSEMBL_RELEASE,
            account=account,
            pool_recycle=1000,
        )


class TestSyntenicRegions(TestCase):
    comp = Compara(
        ["human", "chimp", "macaque"], account=account, release=ENSEMBL_RELEASE
    )
    syntenic_args = dict(align_method="EPO", align_clade="primates")

    def test_correct_alignments(self):
        """should return the correct alignments"""
        # following cases have a mixture of strand between ref seq and others
        coords_expected = [
            [
                {
                    "coord_name": 18,
                    "end": 213739,
                    "species": "human",
                    "start": 213639,
                    "strand": -1,
                },
                {
                    "Homo sapiens:chromosome:18:213639-213739:-1": "ATAAGCATTTCCCTTTAGGGCTCTAAGATGAGGTCATCATCGTTTTTAATCCTGAAGAAGGGCTACTGAGTGAGTGCAGATTATTCGGTAAACACT----CTTA",
                    "Macaca mulatta:chromosome:18:13858303-13858397:1": "------GTTTCCCTTTAGGGCTCTAAGATGAGGTCATCATTGTTTTTAATCCTGAAGAAGGGCTACTGA----GTGCAGATTATTCTGTAAATGTGCTTACTTG",
                    "Pan troglodytes:chromosome:18:16601082-16601182:1": "ATAAGCATTTCCCTTTAGGGCTCTAAGATGAGGTCATCATCGTTTTTAATCCTGAAGAAGGGCTACTGA----GTGCAGATTATTCTGTAAACACTCACTCTTA",
                },
            ],
            [
                {
                    "coord_name": 5,
                    "end": 204859,
                    "species": "human",
                    "start": 204759,
                    "strand": 1,
                },
                {
                    "Homo sapiens:chromosome:5:204874-204974:1": "AACACTTGGTATTT----CCCCTTTATGGAGTGAGAGAGATCTTTAAAATATAAACCCTTGATAATATAATATTACTACTTCCTATTA---CCTGTTATGCAGTTCT",
                    "Macaca mulatta:chromosome:6:1297736-1297840:-1": "AACTCTTGGTGTTTCCTTCCCCTTTATGG---GAGAGAGATCTTTAAAATAAAAAACCTTGATAATATAATATTACTACTTTCTATTATCATCTGTTATGCAGTTCT",
                    "Pan troglodytes:chromosome:5:335911-336011:1": "AACACTTGGTAGTT----CCCCTTTATGGAGTGAGAGAGATCTTTAAAATATAAACCCTTGATAATATAATATTACTACTTTCTATTA---CCTGTTATGCAGTTCT",
                },
            ],
            [
                {
                    "coord_name": 18,
                    "end": 203270,
                    "species": "human",
                    "start": 203170,
                    "strand": -1,
                },
                {
                    "Homo sapiens:chromosome:18:203170-203270:-1": "GGAATAATGAAAGCAATTGTGAGTTAGCAATTACCTTCAAAGAATTACATTTCTTATACAAAGTAAAGTTCATTACTAACCTTAAGAACTTTGGCATTCA",
                    "Pan troglodytes:chromosome:18:16611584-16611684:1": "GGAATAATGAAAGCAATTGTAAGTTAGCAATTACCTTCAAAGAATTACATTTCTTATACAAAGTAAAGTTCATTACTAACCTTAAGAACTTTGGCATTCA",
                },
            ],
            [
                {
                    "coord_name": 2,
                    "end": 46445,
                    "species": "human",
                    "start": 46345,
                    "strand": -1,
                },
                {
                    "Homo sapiens:chromosome:2:46345-46445:-1": "CTACCACTCGAGCGCGTCTCCGCTGGACCCGGAACCCCGGTCGGTCCATTCCCCGCGAAGATGCGCGCCCTGGCGGCCCTGAGCGCGCCCCCGAACGAGC",
                    "Pan troglodytes:chromosome:2a:36792-36892:-1": "CTACCACTCGAGCGCGTCTCCGCTGGACCCGGAACCCCAGTCGGTCCATTCCCCGCGAAGATGCGCGCCCTGGCGGCCCTGAACGCGCCCCCGAACGAGC",
                },
            ],
            [
                {
                    "coord_name": 18,
                    "end": 268049,
                    "species": "human",
                    "start": 267949,
                    "strand": -1,
                },
                {
                    "Homo sapiens:chromosome:18:267949-268049:-1": "GCGCAGTGGCGGGCACGCGCAGCCGAGAAGATGTCTCCGACGCCGCCGCTCTTCAGTTTGCCCGAAGCGCGGACGCGGTTTACGGTGAGCTGTAGAGGGG",
                    "Macaca mulatta:chromosome:18:13805604-13805703:1": "GCGCAG-GGCGGGCACGCGCAGCCGAGAAGATGTCTCCGACGCCGCCGCTCTTCAGTTTGCCCGAAGCGCGGACGCGGTTTACGGTGAGCTGTAGGCGGG",
                    "Pan troglodytes:chromosome:18:16546800-16546900:1": "GCGCAGTGGCGGGCACGCGCAGCCGAGAAGATGTCTCCGACGCCGCCGCTCTTCAGTTTGCCCGAAGCGCGGACGCGGTTTACGGTGAGCTGTAGCGGGG",
                },
            ],
        ]
        for coord, expect in coords_expected:
            coord.update(self.syntenic_args)
            syntenic = list(self.comp.get_syntenic_regions(**coord))[0]
            # check the slope computed from the expected and returned
            # coordinates is ~ 1
            got_names = dict(
                [
                    (n.split(":")[0], n.split(":"))
                    for n in syntenic.get_alignment().names
                ]
            )
            exp_names = dict(
                [(n.split(":")[0], n.split(":")) for n in list(expect.keys())]
            )
            for species in exp_names:
                exp_chrom = exp_names[species][2]
                got_chrom = got_names[species][2]
                self.assertEqual(exp_chrom.lower(), got_chrom.lower())
                exp_start, exp_end = list(map(int, exp_names[species][3].split("-")))
                got_start, got_end = list(map(int, got_names[species][3].split("-")))
                slope = calc_slope(exp_start, exp_end, got_start, got_end)
                assert_allclose(abs(slope), 1.0, atol=1e-3)

    def test_failing_region(self):
        """should correctly handle queries where multiple Ensembl have
        genome block associations for multiple coord systems"""
        gene = self.comp.Human.get_gene_by_stableid(stableid="ENSG00000188554")
        # this should simply not raise any exceptions
        syntenic_regions = list(
            self.comp.get_syntenic_regions(
                region=gene, align_method="PECAN", align_clade="vertebrates"
            )
        )

    def test_syntenic_species_missing(self):
        """should not fail when a compara species has no syntenic region"""
        region = self.comp.Human.get_region(coord_name=2, start=46345, end=46445)
        syntenic = list(
            self.comp.get_syntenic_regions(region=region, **self.syntenic_args)
        )[0]
        species = syntenic.get_species_set()
        self.assertEqual(species, {"Homo sapiens", "Pan troglodytes"})


if __name__ == "__main__":
    main()
