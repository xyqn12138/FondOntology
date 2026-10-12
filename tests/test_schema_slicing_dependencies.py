"""Generic recall regressions on an independently named synthetic T-BOX."""
from dataclasses import replace
from pathlib import Path
import unittest

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import OWL, RDF, RDFS, XSD

from fondontology.qa.graph import build_stack
from fondontology.qa.index import OntologyIndex
from fondontology.qa.schema_retriever import SchemaRetriever

F = Namespace("https://ontology.example.cn/cnfo/ontology/")


class SchemaDependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = build_stack(
            Path(__file__).resolve().parents[1] / "ontology/modules/cnfo-domain.ttl")

    def retriever(self, graph, cap=10000):
        stack = replace(self.stack, tbox=graph, abox=Graph(), _combined=None)
        return SchemaRetriever(OntologyIndex(stack), max_chars=cap)

    def add_class(self, graph, name, label):
        uri = F[name]
        graph.add((uri, RDF.type, OWL.Class))
        graph.add((uri, RDFS.label, Literal(label, lang="zh")))
        return uri

    def add_property(self, graph, name, label, domain, range_, object_=False):
        uri = F[name]
        graph.add((uri, RDF.type, OWL.ObjectProperty if object_ else OWL.DatatypeProperty))
        graph.add((uri, RDFS.label, Literal(label, lang="zh")))
        graph.add((uri, RDFS.domain, domain))
        graph.add((uri, RDFS.range, range_))
        return uri

    def test_temporal_dependency_follows_measure_domain(self):
        graph = Graph()
        sample = self.add_class(graph, "Observation72", "观测记录")
        self.add_property(graph, "measure72", "温度读数", sample, XSD.decimal)
        self.add_property(graph, "moment72", "采样时点", sample, XSD.dateTime)
        other = self.add_class(graph, "Unrelated72", "远端装置")
        self.add_property(graph, "otherMoment72", "远端时点", other, XSD.dateTime)
        result = self.retriever(graph).retrieve("最近一周温度读数的变化")
        self.assertIn("measure72", result.properties)
        self.assertIn("moment72", result.properties)
        self.assertNotIn("otherMoment72", result.properties)

    def test_interval_dates_are_inherited_without_iri_aliases(self):
        graph = Graph()
        base = self.add_class(graph, "Summary73", "汇总记录")
        child = self.add_class(graph, "Weekly73", "周度汇总")
        graph.add((child, RDFS.subClassOf, base))
        for name, label in (("begin73", "起始时点"), ("end73", "结束时点")):
            self.add_property(graph, name, label, base, XSD.date)
        result = self.retriever(graph).retrieve("周度汇总覆盖哪段日期？")
        self.assertTrue({"begin73", "end73"} <= set(result.properties))

    def test_container_bridge_survives_scalar_hits(self):
        graph = Graph()
        container = self.add_class(graph, "Assembly74", "设备集合")
        part = self.add_class(graph, "Part74", "设备元件")
        self.add_property(graph, "contains74", "包含元件", container, part, True)
        self.add_property(graph, "mass74", "元件重量", part, XSD.decimal)
        result = self.retriever(graph).retrieve("设备集合中设备元件的重量")
        self.assertTrue({"contains74", "mass74"} <= set(result.properties))
        self.assertTrue(result.paths)

    def test_unrelated_longer_class_label_does_not_consume_field_packet(self):
        graph = Graph()
        sample = self.add_class(graph, "Meter75", "传感设备")
        self.add_property(graph, "value75", "测量读数", sample, XSD.decimal)
        for number in range(10):
            self.add_class(graph, f"Noise75_{number}", "传感设备配置策略" + str(number))
        result = self.retriever(graph, 200).retrieve("传感设备的测量读数")
        self.assertIn("value75", result.properties)
        self.assertFalse(any(name.startswith("Noise") for name in result.classes))
        self.assertLessEqual(result.char_count, 200)

    def test_unknown_generic_field_does_not_expand_all_domains(self):
        graph = Graph()
        sample = self.add_class(graph, "Sensor76", "采样设备")
        other = self.add_class(graph, "Else76", "订购事务")
        self.add_property(graph, "cost76", "事务金额", other, XSD.decimal)
        result = self.retriever(graph).retrieve("采样设备的金额是多少？")
        self.assertNotIn("cost76", result.properties)

    def test_charge_normalization_is_symmetric(self):
        graph = Graph()
        sample = self.add_class(graph, "Transaction77", "账单事务")
        self.add_property(graph, "description77", "费用名称", sample, XSD.string)
        result = self.retriever(graph).retrieve("账单事务的收费名称")
        self.assertIn("description77", result.properties)

    def test_fund_word_does_not_invent_absent_class(self):
        graph = Graph()
        self.add_class(graph, "Sensor78", "采样设备")
        result = self.retriever(graph).retrieve("基金的金额")
        self.assertNotIn("Fund", result.classes)
