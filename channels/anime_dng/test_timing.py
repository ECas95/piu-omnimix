import unittest
from fractions import Fraction as F
import simfile as S

class TimingChecks(unittest.TestCase):
    def test_offsets_and_bpm_changes(self):
        c=S.Clock({'OFFSET':'1.25','BPMS':'0=120,4=60'})
        self.assertAlmostEqual(c.seconds(4),.75)
        self.assertAlmostEqual(c.seconds(6),2.75)
    def test_stop_after_note_delay_before_note(self):
        c=S.Clock({'BPMS':'0=120','STOPS':'4=2','DELAYS':'4=1'})
        self.assertAlmostEqual(c.seconds(4),3)
        self.assertAlmostEqual(c.seconds(5),5.5)
    def test_warp_and_pause_inside_warp(self):
        c=S.Clock({'BPMS':'0=120','WARPS':'4=4','STOPS':'6=1'})
        self.assertAlmostEqual(c.seconds(9),3.5)
        self.assertFalse(c.judgable(F(5)))
        self.assertTrue(c.judgable(F(6)))
        self.assertTrue(c.judgable(F(8)))
    def test_fake_regions_are_not_attacks(self):
        c=S.Clock({'BPMS':'0=120','FAKES':'4=2'})
        self.assertFalse(c.judgable(4));self.assertTrue(c.judgable(6))
    def test_escaped_semicolon_and_comments(self):
        data=b'#TITLE:A\\;B;\n#BPMS:0=120;\n#NOTES:pump-single::Hard:10:0,0,0,0,0:\n10000 // count 100 L\n00000\n00000\n00000\n;'
        meta,charts=S.parse(data,extension='.sm')
        self.assertEqual(meta['TITLE'],'A;B')
        notes,audit=S.events(charts[0],native=True)
        self.assertEqual(len(notes),1);self.assertEqual(notes[0]['lane'],0)
        self.assertFalse(audit)
    def test_per_chart_ssc_clock(self):
        data=b'#BPMS:0=120;#OFFSET:1;#NOTEDATA:;#STEPSTYPE:dance-single;#DIFFICULTY:Hard;#METER:5;#OFFSET:0;#BPMS:0=60;#NOTES:1000\n0000\n0100\n0000;'
        _,charts=S.parse(data)
        notes,_=S.events(charts[0])
        self.assertEqual([n['ms'] for n in notes],[0.,2000.])
    def test_colon_adjacent_ssc_comments(self):
        data=b'#BPMS:0=120;#NOTEDATA:;#STEPSTYPE:dance-single;#DIFFICULTY:Hard;#METER:5;#NOTES:// measure 0\n1000\n0000\n0100\n0000;'
        _,charts=S.parse(data)
        self.assertEqual([n['ms'] for n in S.events(charts[0])[0]],[0.,1000.])
    def test_ddr_unmatched_tails_are_non_attacks(self):
        data=b'#BPMS:0=120;#NOTES:dance-single::Hard:5:0,0,0,0,0:\n3000\n0000\n0100\nH000;'
        _,charts=S.parse(data)
        notes,audit=S.events(charts[0]);self.assertEqual(len(notes),1)
        self.assertEqual(audit['unmatched_non_attack_tails'],1)
        self.assertEqual(audit['non_attack_H'],1)
    def test_native_invalid_tails_remain_blocked(self):
        data=b'#BPMS:0=120;#NOTES:pump-single::Hard:5:0,0,0,0,0:\n30000\n00000\n01000\n00000;'
        _,charts=S.parse(data)
        with self.assertRaisesRegex(ValueError,'Orphan tail'):S.events(charts[0],native=True)

    def test_native_hold_tail_inside_warp_keeps_release(self):
        from nx_adapter import native_source_cells,native_nx,Q,nx20
        c={'mode':'pump-single','meter':'10','signature':'warp-fixture','source_file_sha256':'fixture',
           'timing':{'BPMS':'0=120','WARPS':'4=4'},'rows':[['0','20000'],['5','30000'],['9','01000']]}
        notes,_=S.events(c,native=True);source,repairs=native_source_cells(c,notes,S.Clock(c['timing']))
        self.assertIn((F(8),0,'3'),source);self.assertEqual(c['rows'][1],['5','30000'])
        self.assertEqual(repairs[0]['unchanged_release_ms'],2000.)
        raw,proof=native_nx(c,8);decoded=Q.notes_of(nx20.parse(raw))
        self.assertEqual(len(decoded),2);self.assertAlmostEqual(decoded[0][4],2000.,places=3)
        self.assertTrue(proof['native_panels_preserved'])

    def test_native_warp_tail_collision_is_not_silently_overwritten(self):
        from nx_adapter import native_source_cells
        c={'timing':{'BPMS':'0=120','WARPS':'4=4'},'mode':'pump-single',
           'rows':[['0','20000'],['5','30000'],['8','10000']]}
        notes,_=S.events(c,native=True)
        with self.assertRaisesRegex(AssertionError,'collide at warp exit'):
            native_source_cells(c,notes,S.Clock(c['timing']))

if __name__=='__main__':unittest.main()
