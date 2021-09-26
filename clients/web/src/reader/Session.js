import React, { useCallback, useContext, useEffect, useMemo, useState } from "react"
import { useQuery } from "../hooks/backend"

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
   readTime
   starTime
}`

const SESSION_QUERY = `query ($feedId: Int, $onlyUnread: Boolean, $onlyStarred: Boolean, $entriesLimit: Int!) {
   session(feedId: $feedId, onlyUnread: $onlyUnread, onlyStarred: $onlyStarred) {
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

export const ENTRIES_LIMIT = 50

export const useSession = ({ feedId, onlyUnread, onlyStarred }) => {
   const [timestamp, setTimestamp] = useState(() => Date.now())
   const [feeds, setFeeds] = useState([])
   const [feedsById, setFeedsById] = useState({})
   const [unreadEntries, setUnreadEntries] = useState(0)
   const [starredEntries, setStarredEntries] = useState(0)
   const [entryIds, setEntryIds] = useState([])
   const [entries, setEntries] = useState([])

   const [entriesOffset, setEntriesOffset] = useState(0)

   const sessionQueryVariables = useMemo(() => {
      if (timestamp) {
         return { feedId, onlyUnread, onlyStarred, entriesLimit: ENTRIES_LIMIT }
      }
   }, [timestamp, feedId, onlyUnread, onlyStarred])

   useEffect(() => {
      setEntryIds([])
      setEntries([])
      setEntriesOffset(0)
   }, [sessionQueryVariables])

   const consumeSessionData = useCallback(({ session }) => {
      setFeeds(session.feeds)
      setFeedsById(session.feeds.reduce((feedsById, feed) => ({ ...feedsById, [feed.id]: feed })))
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

   const refresh = useCallback(() => {
      setTimestamp(new Date())
   }, [])

   return {
      feedId,
      onlyUnread,
      onlyStarred,
      isLoading: sessionIsLoading || entriesAreLoading,
      feeds,
      feedsById,
      entryIds,
      entries,
      unreadEntries,
      starredEntries,
      hasMoreEntries: entries.length < entryIds.length,
      loadMoreEntries,
      refresh,
   }
}

const SessionContext = React.createContext()

export const Session = ({ params, children }) => {
   const session = useSession(params)

   return (
      <SessionContext.Provider value={session}>
         {children}
      </SessionContext.Provider>
   )
}

export const useSessionContext = () => useContext(SessionContext)
