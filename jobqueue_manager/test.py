import pandas as pd
from pandas.testing import assert_frame_equal
from django.test import TestCase
from jobqueue_manager.abd_extractor.helpers.extractor_helper import close_cycle_gaps


class ExtractorHelperTests(TestCase):
    @staticmethod
    def test_close_cycle_gaps_with_correct_df():
        """
        close_cycle_gaps returns DataFrame with cylce_id from 1 to n without gaps. Test with already correct DataFrame.
        """
        cycle_id_list = [[1]*10, [2]*20, [3]*5]
        cycle_id_list = [item for sublist in cycle_id_list for item in sublist]
        df = pd.DataFrame(cycle_id_list, columns=['cycle_id'])
        df_correct = pd.DataFrame(cycle_id_list, columns=['cycle_id'])
        df = close_cycle_gaps(df, None)
        assert_frame_equal(df, df_correct)

    @staticmethod
    def test_close_cycle_gaps_with_gapped_df():
        """
        close_cycle_gaps returns DataFrame with cylce_id from 1 to n without gaps. Test with DataFrame with gaps.
        """
        cycle_id_list = [[3]*10, [7]*20, [12]*5, [13]*10, [100]*13]
        cycle_id_list = [item for sublist in cycle_id_list for item in sublist]
        df = pd.DataFrame(cycle_id_list, columns=['cycle_id'])

        cycle_id_list_correct = [[1]*10, [2]*20, [3]*5, [4]*10, [5]*13]
        cycle_id_list_correct = [item for sublist in cycle_id_list_correct for item in sublist]
        df_correct = pd.DataFrame(cycle_id_list_correct, columns=['cycle_id'])

        df = close_cycle_gaps(df, None)
        assert_frame_equal(df, df_correct)

    @staticmethod
    def test_close_cycle_gaps_with_negative_id():
        """
        close_cycle_gaps returns DataFrame with cylce_id from 1 to n without gaps. Test with DataFrame with negative
        cycle_id and gapps.
        """
        cycle_id_list = [[-1]*10, [0]*20, [12]*5, [13]*10, [100]*13]
        cycle_id_list = [item for sublist in cycle_id_list for item in sublist]
        df = pd.DataFrame(cycle_id_list, columns=['cycle_id'])

        cycle_id_list_correct = [[1]*10, [2]*20, [3]*5, [4]*10, [5]*13]
        cycle_id_list_correct = [item for sublist in cycle_id_list_correct for item in sublist]
        df_correct = pd.DataFrame(cycle_id_list_correct, columns=['cycle_id'])

        df = close_cycle_gaps(df, None)
        assert_frame_equal(df, df_correct)
