from django.test import SimpleTestCase

from apps.academics.services.senior_school_curriculum import (
    CurriculumContractError,
    GRADE10_ELECTIVE_BLOCKS,
    GRADE10_SUBJECTS,
    SENIOR_SCHOOL_CLASS_CURRICULUM_CONTRACTS,
    TEMPORARILY_INACTIVE_SUBJECTS,
    build_class_contract,
    build_contract,
    class_contract_summary,
    contract_summary,
    validate_senior_school_contracts,
    validate_subject_combination,
)


class SeniorSchoolCurriculumContractTests(SimpleTestCase):

    def test_supported_levels(self):
        self.assertEqual(build_contract("Grade 10").level, "Grade 10")
        self.assertEqual(build_contract("Form 3").level, "Form 3")
        self.assertEqual(build_contract("Form 4").level, "Form 4")

    def test_grade10_authoritative_subject_catalogue(self):
        contract = build_contract("Grade 10")

        actual = {
            subject.code: (
                subject.name,
                subject.lessons_per_week,
            )
            for subject in contract.subjects
        }

        expected = {
            code: (name, lessons)
            for code, name, lessons, _category, _required in GRADE10_SUBJECTS
        }

        self.assertEqual(actual, expected)

    def test_grade10_has_exactly_four_elective_blocks(self):
        contract = build_contract("Grade 10")

        self.assertEqual(
            tuple(block.code for block in contract.elective_blocks),
            tuple(block[0] for block in GRADE10_ELECTIVE_BLOCKS),
        )

        self.assertEqual(contract.elective_block_lessons, 20)

    def test_grade10_49_weekly_teaching_slots(self):
        contract = build_contract("Grade 10")

        self.assertEqual(contract.core_lessons, 29)
        self.assertEqual(contract.elective_block_lessons, 20)
        self.assertEqual(contract.weekly_teaching_slots, 49)

    def test_grade10_required_subjects_are_required(self):
        contract = build_contract("Grade 10")

        required = {
            subject.code
            for subject in contract.subjects
            if subject.required
        }

        self.assertEqual(
            required,
            {
                "ENG",
                "KIS",
                "EMCM",
                "CRE",
                "PE",
                "CSL",
                "ICT",
                "PRP",
                "GST",
            },
        )

    def test_grade10_french_is_temporarily_inactive(self):
        self.assertEqual(
            TEMPORARILY_INACTIVE_SUBJECTS,
            frozenset({"FRE"}),
        )

    def test_grade10_elective_selection_requires_one_from_each_block(self):
        selected = (
            "ENG",
            "KIS",
            "EMCM",
            "CRE",
            "PE",
            "CSL",
            "ICT",
            "PRP",
            "GST",
            "BIO",
            "CHEM",
            "GEO",
            "BUS",
        )

        validate_subject_combination(
            "Grade 10",
            selected,
        )

    def test_grade10_elective_selection_rejects_missing_block(self):
        selected = (
            "ENG",
            "KIS",
            "EMCM",
            "CRE",
            "PE",
            "CSL",
            "ICT",
            "PRP",
            "GST",
            "BIO",
            "CHEM",
            "GEO",
        )

        with self.assertRaises(CurriculumContractError):
            validate_subject_combination(
                "Grade 10",
                selected,
            )

    def test_grade10_duplicate_subjects_rejected(self):
        selected = (
            "ENG",
            "ENG",
            "KIS",
            "EMCM",
            "CRE",
            "PE",
            "CSL",
            "ICT",
            "PRP",
            "GST",
            "BIO",
            "CHEM",
            "GEO",
            "BUS",
        )

        with self.assertRaises(CurriculumContractError):
            validate_subject_combination(
                "Grade 10",
                selected,
            )

    def test_form3_and_form4_have_east_and_west_contracts(self):
        self.assertEqual(
            set(SENIOR_SCHOOL_CLASS_CURRICULUM_CONTRACTS),
            {"3E", "3W", "4E", "4W"},
        )

    def test_every_form3_form4_class_has_49_periods(self):
        for group_code in ("3E", "3W", "4E", "4W"):
            contract = build_class_contract(group_code)

            self.assertEqual(
                contract.total_weekly_periods,
                49,
                group_code,
            )

    def test_form3_east_exact_standalone_quantities(self):
        contract = build_class_contract("3E")

        actual = {
            subject.code: subject.lessons_per_week
            for subject in contract.standalone_subjects
        }

        expected = {
            "MAT": 5,
            "ENG": 5,
            "KIS": 5,
            "CHEM": 2,
            "BIO": 2,
            "PHY": 2,
            "CSL": 2,
            "PPI": 1,
        }

        self.assertEqual(actual, expected)
        self.assertEqual(contract.block_lessons, 17)
        self.assertEqual(contract.activity_lessons, 8)
        self.assertEqual(contract.standalone_lessons, 24)

    def test_form3_west_exact_standalone_quantities(self):
        contract = build_class_contract("3W")

        actual = {
            subject.code: subject.lessons_per_week
            for subject in contract.standalone_subjects
        }

        expected = {
            "MAT": 5,
            "ENG": 5,
            "KIS": 5,
            "BIO": 2,
            "CS": 2,
            "PE": 1,
        }

        self.assertEqual(actual, expected)
        self.assertEqual(contract.block_lessons, 17)
        self.assertEqual(contract.activity_lessons, 12)
        self.assertEqual(contract.standalone_lessons, 20)

    def test_form4_east_exact_standalone_quantities(self):
        contract = build_class_contract("4E")

        actual = {
            subject.code: subject.lessons_per_week
            for subject in contract.standalone_subjects
        }

        expected = {
            "MAT": 5,
            "ENG": 5,
            "KIS": 5,
            "CHEM": 3,
            "BIO": 2,
            "PHY": 2,
            "PE": 1,
        }

        self.assertEqual(actual, expected)
        self.assertEqual(contract.block_lessons, 17)
        self.assertEqual(contract.activity_lessons, 9)
        self.assertEqual(contract.standalone_lessons, 23)

    def test_form4_west_exact_standalone_quantities(self):
        contract = build_class_contract("4W")

        actual = {
            subject.code: subject.lessons_per_week
            for subject in contract.standalone_subjects
        }

        expected = {
            "MAT": 5,
            "ENG": 5,
            "KIS": 5,
            "BIO": 2,
            "PHY": 2,
            "CS": 2,
            "PE": 1,
        }

        self.assertEqual(actual, expected)
        self.assertEqual(contract.block_lessons, 17)
        self.assertEqual(contract.activity_lessons, 10)
        self.assertEqual(contract.standalone_lessons, 22)

    def test_east_and_west_do_not_have_identical_standalone_contracts(self):
        self.assertNotEqual(
            build_class_contract("3E").standalone_subjects,
            build_class_contract("3W").standalone_subjects,
        )

        self.assertNotEqual(
            build_class_contract("4E").standalone_subjects,
            build_class_contract("4W").standalone_subjects,
        )

    def test_all_streams_share_same_parallel_block_quantities(self):
        expected = {
            "SCIENCE": 5,
            "HUMANITIES": 4,
            "RELIGIOUS_EDUCATION": 4,
            "TECHNICALS_APPLIED": 4,
        }

        for group_code in ("3E", "3W", "4E", "4W"):
            actual = {
                block.code: block.lessons_per_week
                for block in build_class_contract(group_code).parallel_blocks
            }

            self.assertEqual(actual, expected)

    def test_class_contract_summary_exposes_the_three_layers(self):
        summary = class_contract_summary("3E")

        self.assertEqual(summary["standalone_lessons"], 24)
        self.assertEqual(summary["parallel_block_lessons"], 17)
        self.assertEqual(summary["activity_lessons"], 8)
        self.assertEqual(summary["total_weekly_periods"], 49)

    def test_form_level_summary_exposes_both_streams(self):
        form3 = contract_summary("Form 3")
        form4 = contract_summary("Form 4")

        self.assertEqual(
            set(form3["class_groups"]),
            {"3E", "3W"},
        )

        self.assertEqual(
            set(form4["class_groups"]),
            {"4E", "4W"},
        )

        self.assertEqual(
            form3["class_groups"]["3E"]["total_weekly_periods"],
            49,
        )

        self.assertEqual(
            form3["class_groups"]["3W"]["total_weekly_periods"],
            49,
        )

        self.assertEqual(
            form4["class_groups"]["4E"]["total_weekly_periods"],
            49,
        )

        self.assertEqual(
            form4["class_groups"]["4W"]["total_weekly_periods"],
            49,
        )

    def test_complete_curriculum_contract_validation(self):
        validate_senior_school_contracts()
