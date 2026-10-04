import importlib.util
import shutil
import unittest
from pathlib import Path
from lxml import html

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('report_renderer',ROOT/'.agents/skills/mentortrace/scripts/render_bilingual_report.py')
renderer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)

@unittest.skipUnless(shutil.which('pandoc'),'Pandoc required for actual Markdown rendering')
class ReportLayout(unittest.TestCase):
    def test_shared_plan_is_outside_card_for_both_heading_forms(self):
        for plan in ('#### Revision plan for this group / 本组修改方案','**Revision plan for this group / 本组修改方案**'):
            with self.subTest(plan=plan):
                md=f'''# Report

## Content and technical comments / 内容与技术意见

### Group / 分组

#### 1. One / 第一

**Revision priority:** High

**Comment:** First problem.

**评审意见：** 第一个问题。

#### 2. Two / 第二

**Comment:** Second problem.

**评审意见：** 第二个问题。

{plan}

**Suggested revision:** Shared repair.

**建议修改：** 统一修改。

### 3. Separate / 独立意见

**Comment:** Local issue.

**评审意见：** 局部问题。

**Suggested revision:** Local repair.

**建议修改：** 局部修改。
'''
                rendered,count,_=renderer.build_html(md,'style.css',shutil.which('pandoc'))
                doc=html.fromstring(rendered)
                self.assertEqual(count,3)
                group=doc.xpath('//section[@class="revision-group"]')[0]
                self.assertEqual(len(group.xpath('./article')),2)
                self.assertIn('high',group.xpath('./article')[0].get('class'))
                self.assertEqual(len(group.xpath('./section[@class="group-revision-plan"]')),1)
                self.assertFalse(doc.xpath('//article[contains(@class,"finding-card")]//*[contains(@class,"plan-heading")]'))
                self.assertEqual(len(doc.xpath('//p[contains(@class,"revision-start")]')),2)

    def test_math_and_separate_draft_label(self):
        md=r'''# Report

**Manuscript:** *Sample paper*.

**稿件：**《Sample paper》。

## Content and technical comments / 内容与技术意见

#### 1. Frequency \(f_0\) / 频率

**Comment:** Use \(\sigma^2\).

**Original:** Eq. (2):

\[Y_{n,m}=\sqrt{P}s_{n,m}H_{n,m}+z_{n,m}.\]

#### Draft / 草稿

**Suggested wording / 建议文本:**

Replacement paragraph.
'''
        rendered,_,_=renderer.build_html(md,'style.css',shutil.which('pandoc'))
        doc=html.fromstring(rendered)
        self.assertEqual(len(doc.xpath('//div[@class="metadata-grid"]/div')),2)
        self.assertTrue(doc.xpath('//*[local-name()="math"]'))
        self.assertTrue(doc.xpath('//*[local-name()="math" and @display="block"]'))
        draft=doc.xpath('//article[contains(@class,"draft-card")]')[0]
        self.assertEqual(len(draft.xpath('./p')),2)
        self.assertEqual(''.join(draft.xpath('./p')[1].itertext()).strip(),'Replacement paragraph.')

    def test_bilingual_source_panels_and_full_formula_draft(self):
        md=r'''# Report

## Content and technical comments / 内容与技术意见

### Sample group / 示例组

#### 1. Sample / 示例

**Revision priority:** High

**Location:** Page 1, Eq. (1).

**Original:** The response is

\[y=x+z.\]

**Comment:** State the condition.

**Suggested revision:** Add the condition.

**修改优先级：** 高

**位置：** 第1页式（1）。

**原文：** The response is

\[y=x+z.\]

**审阅意见：** 写明条件。

**建议修改：** 补充条件。

#### Draft / 草稿

**Suggested wording / 建议文本:**

The phase is

\[\theta=2\pi f t.\]

It is small under the stated condition: \( -66.99\,\mathrm{dB}\).
'''
        rendered,_,_=renderer.build_html(md,'style.css',shutil.which('pandoc'))
        doc=html.fromstring(rendered)
        card=doc.xpath('//article[contains(@class,"finding-card")]')[0]
        sources=card.xpath('./div[contains(@class,"source-context")]')
        self.assertEqual(len(sources),2)
        self.assertEqual(len(sources[0].xpath('./p')),3)
        self.assertEqual(len(sources[1].xpath('./p')),3)
        divider=card.xpath('./div[@class="language-divider"]')[0]
        self.assertLess(card.index(divider),card.index(sources[1]))
        draft=doc.xpath('//article[contains(@class,"draft-card")]')[0]
        self.assertEqual(len(draft.xpath('./p')),4)
        self.assertTrue(draft.xpath('.//*[local-name()="math" and @display="block"]'))
        self.assertEqual(len(draft.xpath('.//*[local-name()="math"]')),2)

    def test_compact_chinese_comment_keeps_divider_without_repeated_source(self):
        md='''# Report

## Content and technical comments / 内容与技术意见

### 1. Example / 示例

**Revision priority:** High

**Location:** Page 1, Eq. (2).

**Original:** The response is measured at the receiver.

**Comment:** The receiver is not named.

**Suggested revision:** Name the receiver.

**审阅意见：** 稿件未说明接收方。

**建议修改：** 请说明接收方。
'''
        rendered,_,_=renderer.build_html(md,'style.css',shutil.which('pandoc'))
        card=html.fromstring(rendered).xpath('//article[contains(@class,"finding-card")]')[0]
        self.assertEqual(len(card.xpath('./div[contains(@class,"source-context")]')),1)
        divider=card.xpath('./div[@class="language-divider"]')[0]
        chinese=card.xpath('./p[starts-with(normalize-space(.),"审阅意见：")]')[0]
        self.assertLess(card.index(divider),card.index(chinese))

    def test_alternative_versions_stay_with_suggested_wording_label(self):
        md='''# Report

## Content and technical comments / 内容与技术意见

### Group / 分组

#### 1. Example / 示例

**Comment:** A claim needs a narrower scope.

**审阅意见：** 主张需要限定范围。

#### Draft / 草稿

**Suggested wording / 建议文本:**

**Version A / 版本A:** Narrow claim.

**Version B / 版本B:** Conditional broader claim.
'''
        rendered,_,_=renderer.build_html(md,'style.css',shutil.which('pandoc'))
        doc=html.fromstring(rendered)
        drafts=doc.xpath('//article[contains(@class,"draft-card")]')
        self.assertEqual(len(drafts),1)
        self.assertEqual(len(drafts[0].xpath('./p')),3)
        self.assertIn('Conditional broader claim',''.join(drafts[0].itertext()))

if __name__=='__main__':unittest.main()
