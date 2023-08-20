from .base_api import BaseApi
from .league import League

class Drafts(BaseApi):
	def __init__(self, draft_id):
		self.draft_id = draft_id
		self._base_url = "https://api.sleeper.app/v1/draft/{}".format(self.draft_id)

	def get_specific_draft(self):
		"""gets the draft specified by the draft_id"""
		return self._call(self._base_url)

	def get_all_picks(self):
		"""gets all the picks in the draft specified by the draft_id"""
		return self._call("{}/{}".format(self._base_url,"picks"))

	def get_traded_picks(self):
		"""gets all traded picks in the draft specified by the draft_id"""
		return self._call("{}/{}".format(self._base_url,"traded_picks"))

	def get_all_drafts(self, league_id):
		"""
		getting all previous years' keeper and draft round info
		"""
		league = League(league_id)
		all_drafts = []
		all_final_rosters = []
		# all_user_maps = []
		while True:
			try:
				prev_league_id = league._league['previous_league_id']
				league = League(prev_league_id)
				all_final_rosters.append(league.get_rosters())
				# all_user_maps.append(league.map_users_to_team_name())
				season = league._league['season']
				print(season)
				draft_id = league._league['draft_id']
				current_draft = Drafts(draft_id)
				# pdb.set_trace()
				all_drafts.append(current_draft.get_all_picks())
			except TypeError:
				print("TypeError")
				return all_drafts, all_final_rosters