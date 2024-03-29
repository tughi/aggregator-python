import { useCallback, useEffect, useMemo, useState } from "react"
import { useMutation, useQuery } from "../hooks/backend"

const ENTRY_FIELDS = `{
   id
   feedId
   title
   link
   summary { value }
   content { value }
   author { name }
   publishText
   publishTime
   keepTime
   readTime
   starTime
}`

const SESSION_QUERY = `query ($feedId: Int, $onlyUnread: Boolean, $onlyStarred: Boolean, $entriesLimit: Int!, $latestFirst: Boolean, $maxAge: Int) {
   session(feedId: $feedId, onlyUnread: $onlyUnread, onlyStarred: $onlyStarred, latestFirst: $latestFirst, maxAge: $maxAge) {
      entries(limit: $entriesLimit) ${ENTRY_FIELDS}
      entryIds
      feeds {
         id
         faviconUrl
         title
         userTitle
         unreadEntries
      }
      unreadEntries
      starredEntries
   }
}`.replace(/([\n\t ]+)/g, ' ')

const ENTRIES_QUERY = `query ($entryIds: [Int]!) {
   entries(entryIds: $entryIds) ${ENTRY_FIELDS}
}`.replace(/([\n\t ]+)/g, ' ')

const ENTRIES_LIMIT = 50

export const useSession = ({ revision, feedId, onlyUnread, onlyStarred, latestFirst, maxAge }) => {
   const [feeds, setFeeds] = useState([])
   const [feedsById, setFeedsById] = useState({})
   const [unreadEntries, setUnreadEntries] = useState(0)
   const [starredEntries, setStarredEntries] = useState(0)
   const [entryIds, setEntryIds] = useState([])
   const [entries, setEntries] = useState([])

   const [entriesOffset, setEntriesOffset] = useState(0)

   const sessionQueryVariables = useMemo(() => ({
      revision, feedId, onlyUnread, onlyStarred, latestFirst, maxAge, entriesLimit: ENTRIES_LIMIT
   }), [revision, feedId, onlyUnread, onlyStarred, latestFirst, maxAge])

   useEffect(() => {
      setEntryIds([])
      setEntries([])
      setEntriesOffset(0)
   }, [sessionQueryVariables])

   useEffect(() => {
      setFeedsById((feeds || []).reduce((feedsById, feed) => ({ ...feedsById, [feed.id]: feed }), {}))
   }, [feeds])

   const consumeSessionData = useCallback(({ session }) => {
      setFeeds(session.feeds)
      setUnreadEntries(session.unreadEntries)
      setStarredEntries(session.starredEntries)
      setEntryIds(session.entryIds)
      setEntries(session.entries)
   }, [])

   const sessionIsLoading = useQuery({
      query: SESSION_QUERY,
      variables: sessionQueryVariables,
      consumeData: consumeSessionData,
   })

   const entriesQueryVariables = useMemo(() => ({ entryIds: entryIds.slice(entriesOffset, entriesOffset + ENTRIES_LIMIT) }), [entryIds, entriesOffset])

   const consumeEntriesData = useCallback(({ entries }) => {
      setEntries(currentEntries => [...currentEntries, ...entries])
   }, [])

   const entriesAreLoading = useQuery({
      query: ENTRIES_QUERY,
      variables: entriesQueryVariables,
      consumeData: consumeEntriesData,
      ignore: entriesOffset === 0,
   })

   const loadMoreEntries = useCallback(() => {
      setEntriesOffset(entries.length)
   }, [entries])

   const [updateEntryState] = useMutation({
      query: `mutation($entryId: Int!, $keepTime: DateTime, $readTime: DateTime, $starTime: DateTime) {
         result: updateEntryState(id: $entryId, keepTime: $keepTime, readTime: $readTime, starTime: $starTime) {
            entry ${ENTRY_FIELDS}
         }
      }`
   })

   const toggleEntryReadState = useCallback(entry => {
      if (entry.keepTime || !entry.readTime) {
         updateEntryState({
            variables: {
               entryId: entry.id,
               keepTime: null,
               readTime: createTime(),
               starTime: entry.starTime,
            },
            consumeData: ({ result }) => {
               const updatedEntry = result.entry
               setEntries(entries => entries.map(entry => entry.id === updatedEntry.id ? updatedEntry : entry))
               setFeeds(feeds => feeds.map(feed => feed.id === updatedEntry.feedId ? { ...feed, unreadEntries: feed.unreadEntries - 1 } : feed))
               setUnreadEntries(unreadEntries => unreadEntries - 1)
            }
         })
      } else {
         updateEntryState({
            variables: {
               entryId: entry.id,
               keepTime: createTime(),
               readTime: null,
               starTime: entry.starTime,
            },
            consumeData: ({ result }) => {
               const updatedEntry = result.entry
               setEntries(entries => entries.map(entry => entry.id === updatedEntry.id ? updatedEntry : entry))
               setFeeds(feeds => feeds.map(feed => feed.id === updatedEntry.feedId ? { ...feed, unreadEntries: feed.unreadEntries + 1 } : feed))
               setUnreadEntries(unreadEntries => unreadEntries + 1)
            }
         })
      }
   }, [updateEntryState])

   const toggleEntryStarState = useCallback(entry => {
      if (entry.starTime) {
         updateEntryState({
            variables: {
               entryId: entry.id,
               keepTime: entry.keepTime,
               readTime: entry.readTime,
               starTime: null,
            },
            consumeData: ({ result }) => {
               const updatedEntry = result.entry
               setEntries(entries => entries.map(entry => entry.id === updatedEntry.id ? updatedEntry : entry))
               setStarredEntries(starredEntries => starredEntries - 1)
            }
         })
      } else {
         updateEntryState({
            variables: {
               entryId: entry.id,
               keepTime: entry.keepTime,
               readTime: entry.readTime,
               starTime: createTime(),
            },
            consumeData: ({ result }) => {
               const updatedEntry = result.entry
               setEntries(entries => entries.map(entry => entry.id === updatedEntry.id ? updatedEntry : entry))
               setStarredEntries(starredEntries => starredEntries + 1)
            }
         })
      }
   }, [updateEntryState])

   return {
      ...sessionQueryVariables,
      isLoading: sessionIsLoading || entriesAreLoading,
      feeds,
      feedsById,
      entryIds,
      entries,
      unreadEntries,
      starredEntries,
      hasMoreEntries: entries.length < entryIds.length,
      loadMoreEntries,
      toggleEntryReadState,
      toggleEntryStarState,
   }
}

const createTime = () => {
   const date = new Date()
   date.setMilliseconds(0)
   return date.toISOString()
}
