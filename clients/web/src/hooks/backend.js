import axios from "axios"
import { useEffect, useState } from "react"


export const useFeeds = () => {
   const [loading, setLoading] = useState(false)
   const [feeds, setFeeds] = useState([])

   useEffect(() => {
      let cancelRequest

      setLoading(true)

      axios({
         url: '/graphql',
         method: 'post',
         data: {
            query: `{
               feeds {
                  id
                  title
                  userTitle
                  unreadEntries
               }
            }`
         },
         cancelToken: new axios.CancelToken(cancel => cancelRequest = cancel)
      }).then(response => {
         setFeeds(response.data.data.feeds)
         setLoading(false)
      }).catch(error => {
         if (axios.isCancel(error)) {
            return
         }
      })

      return () => {
         cancelRequest()
      }
   }, [])

   return { loading, feeds }
}
